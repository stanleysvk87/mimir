from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin, require_auth
from app.db import get_conn
from app.models import (
    TerminalChunkApprove,
    TerminalChunkOut,
    TerminalSessionIn,
    TerminalSessionOut,
)

router = APIRouter(prefix="/api/terminal", tags=["terminal"], dependencies=[Depends(require_auth)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fts_match(q: str) -> str:
    """Same escaping as routes_entries._fts_match -- every token quoted so
    punctuation in a pasted command (hyphens, pipes, colons) is always
    literal text, never FTS5 query syntax."""
    tokens = q.split()
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in tokens)


_SESSION_SELECT = """
    SELECT s.*, p.name AS project_name,
        (SELECT count(*) FROM terminal_chunks c WHERE c.session_id = s.id) AS chunk_count,
        (SELECT count(*) FROM terminal_chunks c WHERE c.session_id = s.id AND c.needs_review = 1) AS needs_review_count
    FROM terminal_sessions s
    LEFT JOIN projects p ON p.id = s.project_id
"""


def _session_row_to_out(row) -> dict:
    d = dict(row)
    return d


def _chunk_row_to_out(row) -> dict:
    d = dict(row)
    d["redacted"] = bool(d["redacted"])
    d["needs_review"] = bool(d["needs_review"])
    return d


@router.post("/sessions", response_model=TerminalSessionOut)
def create_session(payload: TerminalSessionIn):
    """Called by the tmux-archive ingest script once a pane's log has been
    closed, redacted, and chunked. One call creates the session row plus
    all of its chunks -- chunks never arrive without a parent session."""
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO terminal_sessions
               (host, tmux_session_name, pane_id, project_id, title, started_at, ended_at,
                redaction_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'ingested', ?, ?)""",
            (
                payload.host, payload.tmux_session_name, payload.pane_id, payload.project_id,
                payload.title, payload.started_at, payload.ended_at, now, now,
            ),
        )
        session_id = cur.lastrowid
        for i, chunk in enumerate(payload.chunks):
            conn.execute(
                """INSERT INTO terminal_chunks
                   (session_id, chunk_index, started_at, ended_at, command_hint, text,
                    redacted, needs_review, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, i, chunk.started_at, chunk.ended_at, chunk.command_hint,
                    chunk.text, int(chunk.redacted), int(chunk.needs_review), now,
                ),
            )
        row = conn.execute(f"{_SESSION_SELECT} WHERE s.id = ?", (session_id,)).fetchone()
    return _session_row_to_out(row)


@router.get("/sessions", response_model=list[TerminalSessionOut])
def list_sessions(
    host: str | None = None,
    project_id: int | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
):
    clauses = []
    params: list = []
    if host:
        clauses.append("s.host = ?")
        params.append(host)
    if project_id is not None:
        clauses.append("s.project_id = ?")
        params.append(project_id)
    if since:
        clauses.append("s.started_at >= ?")
        params.append(since)
    if until:
        clauses.append("s.started_at <= ?")
        params.append(until if len(until) > 10 else f"{until}T23:59:59")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"{_SESSION_SELECT} {where} ORDER BY s.started_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_session_row_to_out(r) for r in rows]


@router.get("/sessions/{session_id}", response_model=TerminalSessionOut)
def get_session(session_id: int):
    with get_conn() as conn:
        row = conn.execute(f"{_SESSION_SELECT} WHERE s.id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(404, "session not found")
    return _session_row_to_out(row)


@router.get("/sessions/{session_id}/chunks", response_model=list[TerminalChunkOut])
def get_session_chunks(session_id: int, include_needs_review: bool = True):
    """Full transcript view -- unlike search, this deliberately can include
    needs_review chunks (include_needs_review=true, the default), since
    reading your own session back is not the same trust boundary as it
    showing up for someone typing a search query."""
    clauses = ["session_id = ?"]
    params: list = [session_id]
    if not include_needs_review:
        clauses.append("needs_review = 0")
    where = " AND ".join(clauses)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM terminal_chunks WHERE {where} ORDER BY chunk_index ASC", params
        ).fetchall()
    return [_chunk_row_to_out(r) for r in rows]


@router.get("/search")
def search_chunks(q: str, project_id: int | None = None, limit: int = 40):
    """Search only ever reaches needs_review=0 chunks -- terminal_chunks_fts
    is kept in sync with that gate by the triggers in db.py, so this query
    can't accidentally surface a quarantined chunk no matter how it's
    written. Returns a snippet (via FTS5 snippet()) rather than full chunk
    text, plus session context, so a match in an hours-long session doesn't
    dump the whole thing."""
    if not q or not q.strip():
        return []
    match = _fts_match(q)
    clauses = ["terminal_chunks_fts MATCH ?"]
    params: list = [match]
    if project_id is not None:
        clauses.append("s.project_id = ?")
        params.append(project_id)
    where = " AND ".join(clauses)
    sql = f"""
        SELECT c.id AS chunk_id, c.session_id, c.chunk_index, c.started_at, c.command_hint,
            snippet(terminal_chunks_fts, 0, '>>>', '<<<', '…', 12) AS snippet,
            s.tmux_session_name, s.host, s.title AS session_title, s.project_id,
            p.name AS project_name
        FROM terminal_chunks_fts
        JOIN terminal_chunks c ON c.id = terminal_chunks_fts.rowid
        JOIN terminal_sessions s ON s.id = c.session_id
        LEFT JOIN projects p ON p.id = s.project_id
        WHERE {where}
        ORDER BY c.started_at DESC
        LIMIT ?
    """
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.patch("/chunks/{chunk_id}/approve", response_model=TerminalChunkOut)
def approve_chunk(chunk_id: int, payload: TerminalChunkApprove):
    """Human review step for a quarantined chunk. `text` lets you fix up
    the redaction (e.g. widen it) while approving in the same call --
    omit it to approve the text exactly as the ingest script left it.
    Setting needs_review=0 here is what makes db.py's terminal_chunks_au_add
    trigger add the row to the FTS index -- this is the only path a
    quarantined chunk can become searchable."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM terminal_chunks WHERE id = ?", (chunk_id,)).fetchone()
        if not row:
            raise HTTPException(404, "chunk not found")
        new_text = payload.text if payload.text is not None else row["text"]
        conn.execute(
            "UPDATE terminal_chunks SET text = ?, needs_review = 0 WHERE id = ?",
            (new_text, chunk_id),
        )
        row = conn.execute("SELECT * FROM terminal_chunks WHERE id = ?", (chunk_id,)).fetchone()
    return _chunk_row_to_out(row)


@router.delete("/sessions/{session_id}", dependencies=[Depends(require_admin)])
def delete_session(session_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM terminal_sessions WHERE id = ?", (session_id,))
    return {"ok": True}


@router.get("/chunks/needs-review", response_model=list[TerminalChunkOut])
def list_needs_review(limit: int = 50):
    """The actual review queue (not just its size) -- backs the frontend's
    review screen. Deliberately no snippet/redaction here: to review and
    approve a chunk you need to see its real (already-redacted) text."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM terminal_chunks WHERE needs_review = 1 ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_chunk_row_to_out(r) for r in rows]


@router.get("/chunks/needs-review/count")
def needs_review_count():
    """Size of the redaction review queue -- see
    ~/scripts/mimir-review-nudge.py, which nudges over ntfy when this
    grows past a threshold. Without this, a quarantined chunk (real
    content, just hidden from search until approved) could sit forgotten
    indefinitely with nothing surfacing that it's waiting."""
    with get_conn() as conn:
        (count,) = conn.execute(
            "SELECT count(*) FROM terminal_chunks WHERE needs_review = 1"
        ).fetchone()
    return {"needs_review_count": count}
