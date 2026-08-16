# Mímir

If you already work with an AI coding agent, that work already flows
through it — Mímir doesn't add anything new there. It just takes what
would otherwise disappear into one closed chat's history and turns it
into your own, self-hosted, actually-searchable record.

A normal AI conversation has history, but it's locked inside that
provider's own app — you can't really search it, you don't get a
structured overview, and once the session ends it's effectively gone,
buried under the next one. Mímir takes what was already happening through
your AI assistant anyway and stores it itself, as a full-text-searchable
daily log.

The AI agent you point at it (Claude Code, Codex, or anything that can
call a REST API) doesn't take anything away from Mímir or remember
anything between sessions beyond what it would already know from talking
to you — it's stateless. Mímir is what makes ordinary work durable and
yours, not a dossier something else keeps on you.

You don't need the agent, either. Every entry is also just a normal
journal row — searchable, browsable by day, addable by hand through the
same API or the UI. Turn the agent off, or never wire one up, and Mímir
still works as a private, self-hosted daily log with real search.

Named after the Norse keeper of the well of memory and wisdom.

## What it does today

- **Timeline & search** — a browsable day-by-day log with full-text
  search (FTS5, accent-insensitive) across everything.
- **Projects** — a curated index of what you're working on, with
  freeform build-notes, an open checklist per project, and now a
  **cross-source timeline**: entries, auto-logged git commits, and
  captured terminal history for one project, merged and keyword-
  searchable in one feed. The scenario it's built for: come back to a
  project after a year, a bug turns up in some old module, search that
  module's name, and see everything that ever touched it.
- **AI recall** — ask a question in plain language, get an answer woven
  from matching entries *and* matching raw terminal excerpts, cited by
  timestamp.
- **AI handoff briefing** — generates a structured onboarding document
  for one project (current state, what's been tried including dead ends,
  what's open, decisions not to accidentally undo) from its notes,
  timeline, and checklist. Meant for the "someone else has to pick this
  up cold" scenario.
- **AI digest** — a short periodic summary (used by `scripts/weekly-digest.py`
  for a Telegram push).
- **Terminal session archive** — a companion capture pipeline (tmux hooks
  + a redact/chunk/ingest script, not part of this repo — see below)
  feeds full tmux pane transcripts in here as searchable history. Any
  chunk that redaction touches is quarantined (`needs_review`) and
  physically excluded from the search index by a DB trigger until a
  human approves it via the Terminal page — not a soft filter, a hard
  gate.
- **Passive git commit logging** — a small companion script
  (`git-commit-archive.py`, see below) logs commits across your local
  repos into Mímir automatically, so "what did I actually do" doesn't
  depend on remembering to write it down.
- Attachments with OCR (photos/PDFs), threads (group entries into a
  narrative), reminders, on-this-day recall.

## Companion scripts (not in this repo)

Two of the features above depend on small standalone scripts that live
next to this repo, not inside it, because they're host automation
(systemd timers, tmux hooks), not part of the web app:

- **tmux-archive** (`tmux-archive-pipe.sh` + `tmux-archive-ingest.py`) —
  captures, redacts, and chunks tmux pane output into the terminal
  archive. Needs a `.tmux.conf` hook (`pipe-pane`) and a periodic timer.
- **git-commit-archive.py** — scans local git repos and bulk-imports
  recent commits as entries.

Both just call this app's public API (`/api/terminal/sessions`,
`/api/entries/bulk-import`), so you can write your own version, or ask
whatever AI agent you're using to write one for your own workflow —
that's the whole point.

## Using it with an AI agent

Mímir's core doesn't know anything about any particular AI tool — it's
just a REST API. The actual "AI writes your history automatically" part
comes from a short standing instruction you give your agent (e.g. a
`CLAUDE.md`/`AGENTS.md` project file for Claude Code/Codex), roughly:

- **At the start of a session**, read from Mímir before doing anything
  else — open checklist items (`GET /api/checklist?status=open`), the
  project list, and recent entries (`GET /api/entries?since=...`) —
  instead of relying on the agent's own memory of "what was I doing".
- **While working**, write entries as things happen — at real checkpoints
  during the session, not batched at the end (a dropped connection or a
  closed terminal loses anything that wasn't written yet).
- Agree on a small set of tag/category conventions up front (project
  categories, what counts as an entry vs. a checklist item) so the agent
  doesn't invent inconsistent ones per session.

That's the whole trick — no special integration beyond a documented API
and an instruction file the agent reads every time.

## Running it

```
cp .env.example .env   # edit MIMIR_PASSWORD (and optionally MIMIR_ADMIN_PASSWORD)
docker compose up -d --build
```

Open `http://localhost:8430` (or whatever `MIMIR_PORT` you set).

## Design

- Backend: FastAPI + raw SQLite (no ORM), single-password session auth
  (PBKDF2 hash, httponly cookie) plus a **separate** admin password
  (`MIMIR_ADMIN_PASSWORD`) required on every destructive (DELETE)
  endpoint. The idea: the everyday password — the one you'd hand to
  someone taking over a project — should never by itself be enough to
  delete anything. This is an app-level guard, not a real security
  boundary against host/SQL-level access.
- Frontend: React + react-router + Vite + Tailwind v4, PWA-installable.
- No hardcoded personal paths or machine names anywhere in the app —
  everything is configuration you provide in your own `.env`.
- See `docs/IMPORT_FORMAT.md` for how to feed your own notes in.

## License

Apache-2.0.
