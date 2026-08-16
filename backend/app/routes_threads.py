from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_admin, require_auth
from app.db import get_conn

router = APIRouter(prefix="/api/threads", tags=["threads"], dependencies=[Depends(require_auth)])


class ThreadIn(BaseModel):
    name: str
    description: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def list_threads():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.*, COUNT(te.entry_id) AS entry_count
            FROM threads t
            LEFT JOIN thread_entries te ON te.thread_id = t.id
            GROUP BY t.id ORDER BY t.updated_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_thread(payload: ThreadIn):
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO threads (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (payload.name, payload.description, now, now),
        )
        row = conn.execute("SELECT * FROM threads WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.get("/{thread_id}")
def get_thread(thread_id: int):
    with get_conn() as conn:
        thread = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        entries = conn.execute(
            """
            SELECT e.*, p.name AS project_name FROM thread_entries te
            JOIN entries e ON e.id = te.entry_id
            LEFT JOIN projects p ON p.id = e.project_id
            WHERE te.thread_id = ? ORDER BY e.timestamp ASC
            """,
            (thread_id,),
        ).fetchall()
    return {"thread": dict(thread), "entries": [dict(r) for r in entries]}


@router.post("/{thread_id}/entries/{entry_id}")
def add_entry_to_thread(thread_id: int, entry_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO thread_entries (thread_id, entry_id) VALUES (?, ?)",
            (thread_id, entry_id),
        )
        conn.execute("UPDATE threads SET updated_at = ? WHERE id = ?", (_now(), thread_id))
    return {"ok": True}


@router.delete("/{thread_id}/entries/{entry_id}")
def remove_entry_from_thread(thread_id: int, entry_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM thread_entries WHERE thread_id = ? AND entry_id = ?", (thread_id, entry_id)
        )
    return {"ok": True}


@router.delete("/{thread_id}", dependencies=[Depends(require_admin)])
def delete_thread(thread_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    return {"ok": True}
