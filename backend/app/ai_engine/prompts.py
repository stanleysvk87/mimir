def build_recall_prompt(question: str, entries: list[dict], chunks: list[dict] | None = None) -> str:
    """The core differentiator vs. a plain search box: stitch scattered
    entries into connected prose that explains what/how/why, citing
    entries by their timestamp instead of just listing them.

    `chunks` (optional) are raw tmux-archive terminal excerpts (see
    routes_terminal.py) -- unlike entries, these are things that actually
    happened at the keyboard, not a written-up summary. Keeping them in a
    visually distinct block matters: entries are curated, chunks are raw
    and unedited, and the answer should be able to tell the reader which
    kind of evidence a claim rests on."""
    formatted = "\n\n".join(
        f"[{e['timestamp']}] ({e.get('machine') or 'unknown machine'}"
        f"{', project: ' + e['project_name'] if e.get('project_name') else ''})\n"
        f"{e.get('title') or ''}\n{e.get('body') or ''}"
        for e in entries
    )
    chunks_block = ""
    if chunks:
        formatted_chunks = "\n\n".join(
            f"[{c['started_at']}] (raw terminal, {c.get('host') or 'unknown host'}"
            f"{', project: ' + c['project_name'] if c.get('project_name') else ''}"
            f", tmux session {c.get('tmux_session_name') or '?'})\n{c.get('text') or ''}"
            for c in chunks
        )
        chunks_block = (
            "\n\nRaw terminal excerpts that matched (unedited command/output "
            f"history, not a written summary):\n\n{formatted_chunks}"
        )
    return (
        "You are helping someone recall their own personal chronicle -- a "
        "log of things they did, across machines and projects, over time. "
        "Below are the entries that matched their question, in chronological "
        "order, optionally followed by raw terminal excerpts. Answer the "
        "question by weaving all of this into connected, readable prose "
        "that explains what happened, how, and why (not just a bullet list "
        "restating each item). Cite specific moments inline using their "
        "timestamp in brackets, e.g. [2026-07-22T21:15], and make clear "
        "when you're drawing on a raw terminal excerpt vs. a written entry "
        "-- the excerpts are unedited fact, entries are someone's summary. "
        "If nothing here actually answers the question, say so plainly "
        "instead of guessing or inventing details.\n\n"
        f"Question: {question}\n\n"
        f"Entries:\n\n{formatted}{chunks_block}"
    )


def build_digest_prompt(entries: list[dict], period_label: str) -> str:
    """Weekly/period digest -- summarize what happened, grouped sensibly,
    for a short push notification (Telegram), not an exhaustive report."""
    formatted = "\n\n".join(
        f"[{e['timestamp']}] ({e.get('machine') or ''}"
        f"{', ' + e['project_name'] if e.get('project_name') else ''}) "
        f"{e.get('title') or ''} -- {e.get('body') or ''}"
        for e in entries
    )
    return (
        f"Summarize what happened during {period_label}, based on the "
        "personal chronicle entries below. Write it as a short, friendly "
        "digest (roughly 100-200 words) suitable for a Telegram message -- "
        "group related entries by project/theme rather than listing every "
        "single one, and mention anything that looks unresolved or "
        "still-in-progress. No markdown headers, plain text only.\n\n"
        f"Entries:\n\n{formatted}"
    )
