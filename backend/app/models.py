from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    status: str = "live"
    key_paths: str = ""
    notes: str = ""
    category: str = "product"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    key_paths: str | None = None
    notes: str | None = None
    category: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    status: str
    key_paths: str
    notes: str
    category: str
    created_at: str
    updated_at: str


class ProjectListOut(BaseModel):
    """Lightweight shape for GET /api/projects -- excludes `notes`, which
    can be tens of KB of build-notes text per project (e.g. muninn 73KB)
    and isn't needed for a list/overview read. `has_notes` lets a caller
    know whether GET /api/projects/{id} is worth fetching for the full
    text."""

    id: int
    name: str
    description: str
    status: str
    key_paths: str
    category: str
    has_notes: bool
    created_at: str
    updated_at: str


class EntryIn(BaseModel):
    timestamp: str
    machine: str = ""
    project_id: int | None = None
    title: str = ""
    body: str = ""
    tags: str = ""
    source_type: str = "manual_pwa"
    source_ref: str = ""
    commit_ref: str = ""
    sindri_script_id: int | None = None
    is_sensitive: bool = False
    follow_up_date: str | None = None


class EntryUpdate(BaseModel):
    timestamp: str | None = None
    machine: str | None = None
    project_id: int | None = None
    title: str | None = None
    body: str | None = None
    tags: str | None = None
    is_sensitive: bool | None = None
    follow_up_date: str | None = None


class EntrySearchRequest(BaseModel):
    """POST body twin of GET /entries' query params -- same filters, just
    JSON instead of a query string so non-ASCII `q` values never have to
    round-trip through URL-encoding."""

    day: str | None = None
    since: str | None = None
    until: str | None = None
    q: str | None = None
    machine: str | None = None
    project_id: int | None = None
    source_type: str | None = None
    include_sensitive: bool = True
    limit: int = 200
    summary: bool = False


class EntryOut(BaseModel):
    id: int
    timestamp: str
    machine: str
    project_id: int | None
    project_name: str | None = None
    title: str
    body: str
    tags: str
    source_type: str
    source_ref: str
    commit_ref: str
    sindri_script_id: int | None
    is_sensitive: bool
    follow_up_date: str | None
    created_at: str
    updated_at: str


class BulkImportEntry(BaseModel):
    """Generic import format -- see docs/IMPORT_FORMAT.md. `source_ref` is
    the dedup fingerprint: re-importing the same source_ref updates
    content/tags/timestamp but never clobbers is_sensitive/follow_up_date
    once a human has set them by hand."""

    timestamp: str
    machine: str = ""
    project: str | None = None
    title: str = ""
    body: str = ""
    tags: str = ""
    source_type: str = "import_legacy"
    source_ref: str


class BulkImportRequest(BaseModel):
    entries: list[BulkImportEntry]


class ChecklistItemIn(BaseModel):
    text: str
    project_id: int | None = None


class ChecklistItemUpdate(BaseModel):
    text: str | None = None
    status: str | None = None
    project_id: int | None = None


class ChecklistItemOut(BaseModel):
    id: int
    text: str
    status: str
    project_id: int | None
    resolved_at: str | None
    created_at: str
    updated_at: str


class TerminalChunkIn(BaseModel):
    """`redacted`/`needs_review` are set by the ingest script (tmux-archive),
    never recomputed server-side -- the redaction pass has to happen before
    the text leaves the machine, not after."""

    started_at: str
    ended_at: str
    command_hint: str = ""
    text: str
    redacted: bool = False
    needs_review: bool = False


class TerminalSessionIn(BaseModel):
    host: str = ""
    tmux_session_name: str = ""
    pane_id: str = ""
    project_id: int | None = None
    title: str = ""
    started_at: str
    ended_at: str | None = None
    chunks: list[TerminalChunkIn] = []


class TerminalChunkOut(BaseModel):
    id: int
    session_id: int
    chunk_index: int
    started_at: str
    ended_at: str
    command_hint: str
    text: str
    redacted: bool
    needs_review: bool
    created_at: str


class TerminalSessionOut(BaseModel):
    id: int
    host: str
    tmux_session_name: str
    pane_id: str
    project_id: int | None
    project_name: str | None = None
    title: str
    started_at: str
    ended_at: str | None
    redaction_status: str
    chunk_count: int = 0
    needs_review_count: int = 0
    created_at: str
    updated_at: str


class TerminalChunkApprove(BaseModel):
    text: str | None = None
