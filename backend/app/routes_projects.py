from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

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
