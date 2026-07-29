# Bulk import format

`POST /api/entries/bulk-import` accepts a generic, tool-agnostic payload so
anyone can write their own importer for their own note-taking setup —
Mímir's core has no knowledge of any particular source format.

```json
{
  "entries": [
    {
      "timestamp": "2026-07-22T00:00:00Z",
      "machine": "my-laptop",
      "project": "Some Project",
      "title": "Short title",
      "body": "Full text of what happened, why, how.",
      "tags": "disk,migration",
      "source_type": "import_legacy",
      "source_ref": "my-notes/2026-07-22.md#00:00"
    }
  ]
}
```

- `source_ref` is the **dedup fingerprint**. Re-running the same import
  with the same `source_ref` updates that entry's content instead of
  creating a duplicate — safe to run repeatedly (e.g. from a cron job
  watching a notes folder for changes).
- `project` is looked up (or created) by name automatically.
- Fields you can omit: `machine`, `project`, `tags`, `source_type`
  (defaults to `import_legacy`).
- `is_sensitive` and `follow_up_date` are intentionally **not** part of
  bulk-import — those are set by a human in the UI and are never
  overwritten by a re-import.
