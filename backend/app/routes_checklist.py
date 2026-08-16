from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.auth import require_admin, require_auth
from app.db import get_conn
from app.models import ChecklistItemIn, ChecklistItemOut, ChecklistItemUpdate

router = APIRouter(
    prefix="/api/checklist", tags=["checklist"], dependencies=[Depends(require_auth)]
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=list[ChecklistItemOut])
def list_items(status: str | None = None, project_id: int | None = None):
    clauses, params = [], []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM checklist_items {where} ORDER BY created_at DESC", params
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", response_model=ChecklistItemOut)
def create_item(payload: ChecklistItemIn):
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO checklist_items (text, status, project_id, created_at, updated_at)"
            " VALUES (?, 'open', ?, ?, ?)",
            (payload.text, payload.project_id, now, now),
        )
        row = conn.execute(
            "SELECT * FROM checklist_items WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


@router.patch("/{item_id}", response_model=ChecklistItemOut)
def update_item(item_id: int, payload: ChecklistItemUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if fields:
        fields["updated_at"] = _now()
        if fields.get("status") == "done":
            fields["resolved_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with get_conn() as conn:
            conn.execute(
                f"UPDATE checklist_items SET {set_clause} WHERE id = ?",
                (*fields.values(), item_id),
            )
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


@router.delete("/{item_id}", dependencies=[Depends(require_admin)])
def delete_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
    return {"ok": True}
