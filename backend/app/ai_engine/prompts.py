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


def build_handoff_prompt(
    project_name: str,
    notes: str,
    timeline: list[dict],
    open_checklist: list[str],
) -> str:
    """The 'colleague quit, someone else has to pick this up cold' briefing.
    Different job from build_digest_prompt: a digest is 'what happened
    recently', this is 'everything a stranger needs to not start from
    zero' -- current state, what's been tried (including dead ends,
    entries and raw terminal excerpts both), what's still open, and why
    decisions were made where that's known. Longer and more structured is
    correct here; this isn't a push notification."""
    timeline_formatted = "\n\n".join(
        f"[{i['timestamp']}] ({i['type']}, {i.get('machine') or ''})\n"
        f"{i.get('title') or ''}\n{(i.get('text') or '')[:1500]}"
        for i in timeline
    )
    checklist_formatted = "\n".join(f"- {c}" for c in open_checklist) or "(none open)"
    return (
        f"Someone new is taking over the project '{project_name}' and has no "
        "prior context -- write a handoff briefing that gets them productive "
        "without re-reading everything below themselves. Structure it as: "
        "(1) what this project is and why it exists, (2) current state in "
        "plain terms, (3) what's been tried, including things that didn't "
        "work and why (dead ends are exactly as important as what succeeded), "
        "(4) what's still open/unresolved right now, (5) anything that looks "
        "like an important decision or constraint the next person shouldn't "
        "accidentally undo. Cite timestamps in brackets where it helps "
        "establish sequence. Be concrete -- name actual files, bugs, and "
        "commands where the source material does, don't vague it into "
        "generalities. This can run longer than a typical summary; "
        "completeness matters more than brevity here.\n\n"
        f"Project notes (the project's own description of itself):\n{notes or '(none written)'}\n\n"
        f"Open checklist items:\n{checklist_formatted}\n\n"
        f"Chronological history (entries, git commits, and raw terminal excerpts):\n\n{timeline_formatted}"
    )


def build_digest_prompt(entries: list[dict], period_label: str, terminal_stats: dict | None = None) -> str:
    """Weekly/period digest -- summarize what happened, grouped sensibly,
    for a short push notification (Telegram), not an exhaustive report.

    `terminal_stats` (optional) is a small aggregate, not raw chunk text --
    a digest is a ~150-word message, and dumping raw terminal transcripts
    into the prompt would drown the actual summary in noise. It's here so
    the AI can mention "plus N hands-on terminal sessions" as texture,
    the same way it would mention entry counts, without the prompt
    ballooning with unfiltered command/output history."""
    formatted = "\n\n".join(
        f"[{e['timestamp']}] ({e.get('machine') or ''}"
        f"{', ' + e['project_name'] if e.get('project_name') else ''}) "
        f"{e.get('title') or ''} -- {e.get('body') or ''}"
        for e in entries
    )
    stats_line = ""
    if terminal_stats and terminal_stats.get("session_count"):
        stats_line = (
            f"\n\nAlso, separately from the entries above: {terminal_stats['session_count']} "
            f"tmux terminal session(s) were captured across "
            f"{terminal_stats.get('project_count', 0)} project(s) during this period "
            "(raw hands-on work, not written up as entries) -- you can mention this as "
            "a rough measure of hands-on activity, but you don't have their content."
        )
    return (
        f"Summarize what happened during {period_label}, based on the "
        "personal chronicle entries below. Write it as a short, friendly "
        "digest (roughly 100-200 words) suitable for a Telegram message -- "
        "group related entries by project/theme rather than listing every "
        "single one, and mention anything that looks unresolved or "
        "still-in-progress. No markdown headers, plain text only.\n\n"
        f"Entries:\n\n{formatted}{stats_line}"
    )
