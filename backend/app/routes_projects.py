from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.ai_engine import AIEngineError, get_provider
from app.ai_engine.prompts import build_handoff_prompt
from app.auth import require_auth
from app.db import get_conn
from app.models import ProjectIn, ProjectListOut, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_auth)])

_LIST_COLUMNS = (
    "id, name, description, status, key_paths, category,"
    " (length(notes) > 0) AS has_notes, created_at, updated_at"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=None)
def list_projects(category: str | None = None, include_notes: bool = False):
    """Deliberately excludes `notes` by default -- some projects carry
    tens of KB of build-notes text (e.g. muninn ~73KB) which made a plain
    list read unwieldy for a quick overview. Use GET /{project_id} for a
    single project's full `notes`, or `?include_notes=true` here for
    tooling that genuinely needs every project's full text at once (e.g.
    export-mimir-to-logs.py)."""
    columns = "*" if include_notes else _LIST_COLUMNS
    query = f"SELECT {columns} FROM projects"
    params = ()
    if category:
        query += " WHERE category = ?"
        params = (category,)
    query += " ORDER BY name"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    model = ProjectOut if include_notes else ProjectListOut
    return [model(**dict(r)) for r in rows]


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectIn):
    now = _now()
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO projects (name, description, status, key_paths, notes, category, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    payload.name,
                    payload.description,
                    payload.status,
                    payload.key_paths,
                    payload.notes,
                    payload.category,
                    now,
                    now,
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"Project already exists: {exc}") from exc
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if fields:
        fields["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with get_conn() as conn:
            conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                (*fields.values(), project_id),
            )
    return get_project(project_id)


@router.delete("/{project_id}")
def delete_project(project_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return {"ok": True}


def _fts_match(q: str) -> str:
    """Same token-quoting as routes_entries._fts_match / routes_terminal
    -- every token quoted so punctuation in a search term is always
    literal text, never FTS5 query syntax."""
    tokens = q.split()
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def _timeline_items(
    project_id: int,
    q: str | None,
    since: str | None,
    until: str | None,
    limit: int,
) -> list[dict]:
    """Core query behind both GET /{id}/timeline and GET /{id}/handoff --
    see the timeline route's docstring for what this merges and why."""
    entry_clauses = ["e.project_id = ?"]
    entry_params: list = [project_id]
    if q and q.strip():
        entry_clauses.append("e.id IN (SELECT rowid FROM entries_fts WHERE entries_fts MATCH ?)")
        entry_params.append(_fts_match(q))
    if since:
        entry_clauses.append("e.timestamp >= ?")
        entry_params.append(since)
    if until:
        entry_clauses.append("e.timestamp <= ?")
        entry_params.append(until if len(until) > 10 else f"{until}T23:59:59")

    chunk_clauses = ["s.project_id = ?"]
    chunk_params: list = [project_id]
    if q and q.strip():
        chunk_clauses.append("c.id IN (SELECT rowid FROM terminal_chunks_fts WHERE terminal_chunks_fts MATCH ?)")
        chunk_params.append(_fts_match(q))
    if since:
        chunk_clauses.append("c.started_at >= ?")
        chunk_params.append(since)
    if until:
        chunk_clauses.append("c.started_at <= ?")
        chunk_params.append(until if len(until) > 10 else f"{until}T23:59:59")

    with get_conn() as conn:
        entry_rows = conn.execute(
            f"""SELECT e.id, e.timestamp, e.machine, e.title, e.body, e.source_type
                FROM entries e WHERE {' AND '.join(entry_clauses)}""",
            entry_params,
        ).fetchall()
        chunk_rows = conn.execute(
            f"""SELECT c.id, c.started_at AS timestamp, s.host AS machine,
                    c.command_hint, c.text, s.tmux_session_name
                FROM terminal_chunks c JOIN terminal_sessions s ON s.id = c.session_id
                WHERE {' AND '.join(chunk_clauses)}""",
            chunk_params,
        ).fetchall()

    items = []
    for r in entry_rows:
        d = dict(r)
        items.append({
            "type": "git_commit" if d["source_type"] == "git_auto" else "entry",
            "id": d["id"],
            "timestamp": d["timestamp"],
            "machine": d["machine"],
            "title": d["title"],
            "text": d["body"],
        })
    for r in chunk_rows:
        d = dict(r)
        items.append({
            "type": "terminal",
            "id": d["id"],
            "timestamp": d["timestamp"],
            "machine": d["machine"],
            "title": f"tmux: {d['tmux_session_name']} — {d['command_hint']}" if d["command_hint"] else f"tmux: {d['tmux_session_name']}",
            "text": d["text"],
        })

    items.sort(key=lambda i: i["timestamp"])
    return items[:limit]


@router.get("/{project_id}/timeline")
def project_timeline(
    project_id: int,
    q: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 300,
):
    """The 'return to a project after a year' view: merges entries
    (written summaries -- including auto-logged git commits, source_type
    'git_auto') and terminal_chunks (raw command/output history, always
    needs_review=0 only -- quarantined chunks never surface here either)
    for one project into a single chronological feed. `q`, if given,
    filters BOTH sources by the same FTS5 query, so e.g. `?q=core` finds
    every entry, commit, and terminal excerpt that ever mentioned "core"
    for this project -- the actual answer to "where did I touch core and
    when."""
    return _timeline_items(project_id, q, since, until, limit)


@router.get("/{project_id}/handoff")
def project_handoff(project_id: int, limit: int = 120):
    """The 'colleague quit, someone else picks this up cold' briefing --
    see build_handoff_prompt for the framing. Pulls the project's own
    notes, its open checklist items, and its full timeline (entries +
    git commits + terminal excerpts), and asks the AI provider to turn
    that into a structured onboarding document rather than a short
    summary."""
    with get_conn() as conn:
        project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        checklist_rows = conn.execute(
            "SELECT text FROM checklist_items WHERE project_id = ? AND status = 'open' ORDER BY created_at",
            (project_id,),
        ).fetchall()

    timeline = _timeline_items(project_id, None, None, None, limit)
    open_checklist = [r["text"] for r in checklist_rows]

    if not timeline and not project["notes"] and not open_checklist:
        return {"briefing": "Nothing recorded for this project yet.", "item_count": 0}

    try:
        provider = get_provider()
        text = provider.complete(
            build_handoff_prompt(project["name"], project["notes"], timeline, open_checklist)
        )
    except AIEngineError as exc:
        return {"briefing": f"AI unavailable: {exc}", "item_count": len(timeline)}
    return {"briefing": text, "item_count": len(timeline), "open_checklist_count": len(open_checklist)}
