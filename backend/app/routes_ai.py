from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai_engine import AIEngineError, ai_status, get_provider
from app.ai_engine.prompts import build_digest_prompt, build_recall_prompt
from app.auth import require_auth
from app.db import get_conn

router = APIRouter(prefix="/api/ai", tags=["ai"], dependencies=[Depends(require_auth)])


class RecallRequest(BaseModel):
    question: str
    day: str | None = None
    project_id: int | None = None
    limit: int = 40


def _run_query(clauses: list[str], params: list, limit: int) -> list[dict]:
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT e.*, p.name AS project_name FROM entries e
        LEFT JOIN projects p ON p.id = e.project_id
        {where}
        ORDER BY e.timestamp ASC LIMIT ?
    """
    with get_conn() as conn:
        rows = conn.execute(sql, [*params, limit]).fetchall()
    return [dict(r) for r in rows]


def _matching_entries(question: str, day: str | None, project_id: int | None, limit: int) -> list[dict]:
    """Reuses the same naive LIKE search as the Search view. Matches on a
    ~5-char prefix of each word rather than the whole word -- Slovak noun
    declension means the question's word form ("diskami", "victuse")
    often differs from the base form stored in an entry ("disk",
    "victus"); prefix matching tolerates that without a real stemmer."""
    clauses, params = [], []
    words = [w.strip(".,!?:;") for w in question.split()]
    stems = {w[:5].lower() for w in words if len(w) >= 4}
    if stems:
        word_clauses = []
        for stem in stems:
            word_clauses.append("(lower(title) LIKE ? OR lower(body) LIKE ? OR lower(tags) LIKE ?)")
            like = f"%{stem}%"
            params.extend([like, like, like])
        clauses.append(f"({' OR '.join(word_clauses)})")
    if day:
        clauses.append("timestamp LIKE ?")
        params.append(f"{day}%")
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)

    results = _run_query(clauses, params, limit)
    if results or not stems:
        return results

    # Nothing matched any word stem -- fall back to the most recent
    # entries (optionally still scoped to day/project) rather than
    # telling the user "nothing found" on a plausible, answerable
    # question just because of word-form mismatch.
    fallback_clauses = [c for c in clauses if c not in (clauses[0],)] if len(clauses) > 1 else []
    return _run_query(fallback_clauses, params[len(stems) * 3 :], min(limit, 20))


def _matching_chunks(question: str, day: str | None, project_id: int | None, limit: int) -> list[dict]:
    """Terminal-archive counterpart to _matching_entries. Uses real FTS5
    MATCH (not the LIKE-prefix trick above) since terminal_chunks_fts
    already exists and is cheap to query -- and it can only ever return
    needs_review=0 chunks, by construction (see db.py's FTS triggers), so
    a quarantined password/token can never end up inside an AI prompt."""
    words = [w.strip(".,!?:;") for w in question.split() if len(w.strip(".,!?:;")) >= 3]
    if not words:
        return []
    match = " OR ".join('"' + w.replace('"', '""') + '"' for w in words)
    clauses = ["terminal_chunks_fts MATCH ?"]
    params: list = [match]
    if day:
        clauses.append("c.started_at LIKE ?")
        params.append(f"{day}%")
    if project_id is not None:
        clauses.append("s.project_id = ?")
        params.append(project_id)
    where = " AND ".join(clauses)
    sql = f"""
        SELECT c.started_at, c.text, s.host, s.tmux_session_name, p.name AS project_name
        FROM terminal_chunks_fts
        JOIN terminal_chunks c ON c.id = terminal_chunks_fts.rowid
        JOIN terminal_sessions s ON s.id = c.session_id
        LEFT JOIN projects p ON p.id = s.project_id
        WHERE {where}
        ORDER BY c.started_at ASC LIMIT ?
    """
    with get_conn() as conn:
        rows = conn.execute(sql, [*params, limit]).fetchall()
    return [dict(r) for r in rows]


@router.get("/status")
def status():
    return ai_status()


@router.post("/recall")
def recall(payload: RecallRequest):
    entries = _matching_entries(payload.question, payload.day, payload.project_id, payload.limit)
    chunks = _matching_chunks(payload.question, payload.day, payload.project_id, payload.limit)
    if not entries and not chunks:
        return {"answer": "No entries matched that question.", "matched_count": 0}
    try:
        provider = get_provider()
        answer = provider.complete(build_recall_prompt(payload.question, entries, chunks))
    except AIEngineError as exc:
        return {"answer": f"AI unavailable: {exc}", "matched_count": len(entries) + len(chunks)}
    return {"answer": answer, "matched_count": len(entries), "matched_chunk_count": len(chunks)}


@router.get("/digest")
def digest(days: int = 7):
    """Generates (but does not send) a period digest -- the weekly cron
    script calls this and handles delivery (Telegram) itself, so the API
    stays testable/usable on its own."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT e.*, p.name AS project_name FROM entries e
            LEFT JOIN projects p ON p.id = e.project_id
            WHERE e.timestamp > ? ORDER BY e.timestamp ASC
            """,
            (since,),
        ).fetchall()
    entries = [dict(r) for r in rows]
    if not entries:
        return {"digest": "No entries in this period.", "entry_count": 0}
    try:
        provider = get_provider()
        text = provider.complete(build_digest_prompt(entries, f"the last {days} days"))
    except AIEngineError as exc:
        return {"digest": f"AI unavailable: {exc}", "entry_count": len(entries)}
    return {"digest": text, "entry_count": len(entries)}
