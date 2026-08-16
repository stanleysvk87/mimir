from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin, require_auth
from app.db import get_conn
from app.models import BulkImportRequest, EntryIn, EntryOut, EntrySearchRequest, EntryUpdate

router = APIRouter(prefix="/api/entries", tags=["entries"], dependencies=[Depends(require_auth)])

_SELECT = """
    SELECT e.*, p.name AS project_name
    FROM entries e
    LEFT JOIN projects p ON p.id = e.project_id
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SNIPPET_LEN = 240


def _row_to_out(row, summary: bool = False) -> dict:
    d = dict(row)
    d["is_sensitive"] = bool(d["is_sensitive"])
    if summary and len(d["body"]) > _SNIPPET_LEN:
        d["body"] = d["body"][:_SNIPPET_LEN].rstrip() + "…"
    return d


def _fts_match(q: str) -> str:
    """Turn free text into a safe FTS5 MATCH query: every token quoted and
    AND-ed together. Quoting each token means punctuation the caller typed
    (hyphens, colons, parens -- all FTS5 query-syntax characters) is always
    treated as literal text, never as a MATCH operator, so it can't throw
    a syntax error or silently mean something else (e.g. a leading "-"
    would otherwise be NOT)."""
    tokens = q.split()
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def _where(
    day: str | None,
    since: str | None,
    until: str | None,
    q: str | None,
    machine: str | None,
    project_id: int | None,
    source_type: str | None,
    include_sensitive: bool,
) -> tuple[str, list]:
    """Shared filter-clause builder for GET /entries, POST /entries/search
    and GET /entries/count, so the three stay in sync by construction
    instead of by discipline."""
    clauses = []
    params: list = []

    if day:
        clauses.append("e.timestamp LIKE ?")
        params.append(f"{day}%")
    if since:
        clauses.append("e.timestamp >= ?")
        params.append(since)
    if until:
        # a bare YYYY-MM-DD should include the whole day, not just 00:00:00
        clauses.append("e.timestamp <= ?")
        params.append(until if len(until) > 10 else f"{until}T23:59:59")
    if q and q.strip():
        clauses.append(
            "(e.id IN (SELECT rowid FROM entries_fts WHERE entries_fts MATCH ?)"
            " OR EXISTS (SELECT 1 FROM attachments a WHERE a.entry_id = e.id AND a.ocr_text LIKE ?))"
        )
        params.extend([_fts_match(q), f"%{q}%"])
    if machine:
        clauses.append("e.machine = ?")
        params.append(machine)
    if project_id is not None:
        clauses.append("e.project_id = ?")
        params.append(project_id)
    if source_type:
        clauses.append("e.source_type = ?")
        params.append(source_type)
    if not include_sensitive:
        clauses.append("e.is_sensitive = 0")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


@router.get("", response_model=list[EntryOut])
def list_entries(
    day: str | None = None,
    since: str | None = None,
    until: str | None = None,
    q: str | None = None,
    machine: str | None = None,
    project_id: int | None = None,
    source_type: str | None = None,
    include_sensitive: bool = True,
    limit: int = 200,
    summary: bool = False,
):
    """`day` filters to a single calendar day (YYYY-MM-DD prefix match on
    timestamp) -- the Timeline view's primary use. `since`/`until` filter
    an inclusive timestamp range (either can be used alone) for pulling
    more than one day without N separate calls. `q` is an FTS5 fulltext
    search across title/body/tags (accent- and case-insensitive, multi-word
    AND) plus a plain LIKE fallback over attachment OCR text. `summary=true`
    truncates `body` to a short snippet (some entries run several KB) --
    opt-in, default unchanged, so the frontend (which renders full body
    inline) is unaffected; meant for a quick "what happened" scan, then
    GET /{id} for the full entry."""
    where, params = _where(day, since, until, q, machine, project_id, source_type, include_sensitive)
    sql = f"{_SELECT} {where} ORDER BY e.timestamp DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_out(r, summary=summary) for r in rows]


@router.post("/search", response_model=list[EntryOut])
def search_entries(payload: EntrySearchRequest):
    """Same filters/semantics as `GET /entries`, but as a JSON body instead
    of a query string -- added so non-ASCII search terms (Slovak diacritics
    in particular) never have to survive URL-encoding through a shell/curl
    call, which is where that used to break in practice."""
    where, params = _where(
        payload.day, payload.since, payload.until, payload.q,
        payload.machine, payload.project_id, payload.source_type,
        payload.include_sensitive,
    )
    sql = f"{_SELECT} {where} ORDER BY e.timestamp DESC LIMIT ?"
    params.append(payload.limit)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_out(r, summary=payload.summary) for r in rows]


@router.get("/count")
def count_entries(
    day: str | None = None,
    since: str | None = None,
    until: str | None = None,
    q: str | None = None,
    machine: str | None = None,
    project_id: int | None = None,
    source_type: str | None = None,
    include_sensitive: bool = True,
):
    """Total matching rows for the same filters as `GET /entries`, without
    the `limit` truncation -- lets a caller detect "there's more than the
    200 I got back" instead of silently assuming the page was complete."""
    where, params = _where(day, since, until, q, machine, project_id, source_type, include_sensitive)
    sql = f"SELECT count(*) AS n FROM entries e {where}"
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
    return {"total": row["n"]}


@router.get("/days")
def list_days():
    """Distinct calendar days that have at least one entry, most recent
    first -- powers the Timeline's prev/next-day navigation without the
    frontend having to guess which dates exist."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(timestamp, 1, 10) AS day FROM entries ORDER BY day DESC"
        ).fetchall()
    return [r["day"] for r in rows]


@router.get("/sync-status")
def sync_status():
    """Self-check: most recent claude_session entry per machine, so a
    stalled dual-write shows up here instead of going unnoticed for a
    week like the Pi-hole mail report / claude-cache-sync incidents."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT machine, MAX(timestamp) AS last_seen FROM entries"
            " WHERE source_type = 'claude_session' AND machine != ''"
            " GROUP BY machine"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/related")
def related_entries(title: str = "", body: str = "", project_id: int | None = None, exclude_id: int | None = None, limit: int = 5):
    """Lightweight heuristic (not AI) for the "you've dealt with this
    before" suggestion shown while composing a new entry: same project,
    or overlapping significant words in title/body."""
    words = [w for w in f"{title} {body}".split() if len(w) > 4][:8]
    clauses, params = [], []
    or_parts = []
    if project_id is not None:
        or_parts.append("project_id = ?")
        params.append(project_id)
    for w in words:
        or_parts.append("(title LIKE ? OR body LIKE ?)")
        like = f"%{w}%"
        params.extend([like, like])
    if not or_parts:
        return []
    clauses.append(f"({' OR '.join(or_parts)})")
    if exclude_id is not None:
        clauses.append("e.id != ?")
        params.append(exclude_id)
    where = f"WHERE {' AND '.join(clauses)}"
    sql = f"{_SELECT} {where} ORDER BY e.timestamp DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/on-this-day")
def on_this_day(month_day: str):
    """`month_day` is MM-DD. Returns entries from previous years matching
    that calendar day -- the "memories" widget."""
    with get_conn() as conn:
        rows = conn.execute(
            f"{_SELECT} WHERE substr(e.timestamp, 6, 5) = ? AND substr(e.timestamp, 1, 10) != ? ORDER BY e.timestamp DESC",
            (month_day, datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/reminders/due")
def reminders_due():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute(
            f"{_SELECT} WHERE e.follow_up_date IS NOT NULL AND e.follow_up_date <= ? ORDER BY e.follow_up_date ASC",
            (today,),
        ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int):
    with get_conn() as conn:
        row = conn.execute(f"{_SELECT} WHERE e.id = ?", (entry_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _row_to_out(row)


@router.post("", response_model=EntryOut)
def create_entry(payload: EntryIn):
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO entries
                (timestamp, machine, project_id, title, body, tags, source_type,
                 source_ref, commit_ref, sindri_script_id, is_sensitive,
                 follow_up_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.timestamp, payload.machine, payload.project_id, payload.title,
                payload.body, payload.tags, payload.source_type, payload.source_ref,
                payload.commit_ref, payload.sindri_script_id, int(payload.is_sensitive),
                payload.follow_up_date, now, now,
            ),
        )
        entry_id = cur.lastrowid
        row = conn.execute(f"{_SELECT} WHERE e.id = ?", (entry_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{entry_id}", response_model=EntryOut)
def update_entry(entry_id: int, payload: EntryUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if "is_sensitive" in fields:
        fields["is_sensitive"] = int(fields["is_sensitive"])
    if fields:
        fields["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with get_conn() as conn:
            conn.execute(
                f"UPDATE entries SET {set_clause} WHERE id = ?",
                (*fields.values(), entry_id),
            )
    return get_entry(entry_id)


@router.delete("/{entry_id}", dependencies=[Depends(require_admin)])
def delete_entry(entry_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    return {"ok": True}


@router.post("/bulk-import")
def bulk_import(payload: BulkImportRequest):
    """Generic, shareable ingestion endpoint -- see docs/IMPORT_FORMAT.md.
    Upserts by `source_ref` (same dedup pattern as Sindri's
    `_upsert_file`): re-importing the same source_ref updates the content
    fields but never touches `is_sensitive`/`follow_up_date`, which are
    only ever set by a human in the UI."""
    now = _now()
    created, updated = 0, 0
    with get_conn() as conn:
        for item in payload.entries:
            project_id = None
            if item.project:
                # Case-insensitive lookup so a differently-cased mention
                # (e.g. "Homelab" vs. an existing "homelab") reuses the
                # same row instead of creating a case-duplicate (bit us
                # for real with 'Mimir'/'mimir', 2026-07-25).
                row = conn.execute(
                    "SELECT id FROM projects WHERE name = ? COLLATE NOCASE", (item.project,)
                ).fetchone()
                if row:
                    project_id = row["id"]
                else:
                    # 'topic-note', not the schema default 'product' --
                    # an entry mentioning a not-yet-known project name is
                    # an incidental topic, not a hand-curated real
                    # product (those are created deliberately via
                    # POST /api/projects with an explicit category).
                    cur = conn.execute(
                        "INSERT INTO projects (name, description, status, key_paths, category, created_at, updated_at)"
                        " VALUES (?, '', 'live', '', 'topic-note', ?, ?)",
                        (item.project, now, now),
                    )
                    project_id = cur.lastrowid

            existing = conn.execute(
                "SELECT id FROM entries WHERE source_ref = ?", (item.source_ref,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE entries SET timestamp = ?, machine = ?, project_id = ?,
                        title = ?, body = ?, tags = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (item.timestamp, item.machine, project_id, item.title, item.body,
                     item.tags, now, existing["id"]),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO entries
                        (timestamp, machine, project_id, title, body, tags,
                         source_type, source_ref, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item.timestamp, item.machine, project_id, item.title, item.body,
                     item.tags, item.source_type, item.source_ref, now, now),
                )
                created += 1
    return {"created": created, "updated": updated}
