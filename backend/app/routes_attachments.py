import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.auth import require_admin, require_auth
from app.db import get_conn

router = APIRouter(prefix="/api/entries", tags=["attachments"], dependencies=[Depends(require_auth)])

ATTACHMENTS_DIR = Path("/data/attachments")
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_ocr(path: Path) -> str:
    """Best-effort OCR -- if tesseract/pytesseract aren't available for
    whatever reason, the attachment is still saved, just without
    searchable text. Never blocks the upload on OCR failure."""
    try:
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception:
        return ""


@router.post("/{entry_id}/attachments")
async def upload_attachment(entry_id: int, file: UploadFile):
    with get_conn() as conn:
        entry = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix or ""
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = ATTACHMENTS_DIR / stored_name
    content = await file.read()
    stored_path.write_bytes(content)

    ocr_text = _run_ocr(stored_path) if (file.content_type in IMAGE_TYPES) else ""

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO attachments (entry_id, file_path, mime_type, ocr_text, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (entry_id, stored_name, file.content_type or "", ocr_text, _now()),
        )
        row = conn.execute("SELECT * FROM attachments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.get("/{entry_id}/attachments")
def list_attachments(entry_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM attachments WHERE entry_id = ? ORDER BY created_at", (entry_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{entry_id}/attachments/{attachment_id}/file")
def get_attachment_file(entry_id: int, attachment_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT file_path, mime_type FROM attachments WHERE id = ? AND entry_id = ?",
            (attachment_id, entry_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = ATTACHMENTS_DIR / row["file_path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=row["mime_type"] or None)


@router.delete("/{entry_id}/attachments/{attachment_id}", dependencies=[Depends(require_admin)])
def delete_attachment(entry_id: int, attachment_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT file_path FROM attachments WHERE id = ? AND entry_id = ?",
            (attachment_id, entry_id),
        ).fetchone()
        if row:
            (ATTACHMENTS_DIR / row["file_path"]).unlink(missing_ok=True)
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
    return {"ok": True}
