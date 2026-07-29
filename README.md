# Mímir

A self-hosted personal chronicle: one searchable, browsable timeline for
everything you did, when, how, and why — instead of scattered notes files.

Named after the Norse keeper of the well of memory and wisdom.

## Status

Early scaffold (Phase 1 of the build plan): auth, day-timeline view,
fulltext search, and a generic bulk-import API. AI recall, attachments,
threads, and reminders are planned but not built yet.

## Running it

```
cp .env.example .env   # edit MIMIR_PASSWORD
docker compose up -d --build
```

Open `http://localhost:8430` (or whatever `MIMIR_PORT` you set).

## Design

- Backend: FastAPI + raw SQLite (no ORM), single-password auth with a
  PBKDF2 hash and an httponly session cookie.
- Frontend: React + react-router + Vite + Tailwind v4, PWA-installable.
- No hardcoded personal paths or machine names anywhere in the app —
  everything is configuration you provide in your own `.env`.
- See `docs/IMPORT_FORMAT.md` for how to feed your own notes in.

## License

Not yet decided — this stays a local, unpublished project until it's
proven useful in daily use.
