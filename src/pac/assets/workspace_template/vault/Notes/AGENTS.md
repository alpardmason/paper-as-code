# Notes Agent Guide

Deep notes are flexible learning artifacts, not templated reports.

When writing a note:

- Follow the user's prompt for the specific research object.
- Prioritize conceptual understanding over summary.
- Explain mechanisms from first principles when useful.
- Include equations, pseudocode, diagrams, or implementation sketches only when they clarify the idea.
- Merge human annotations, implementation lessons, related sources, and current workspace context when available.
- Recommend related sources as next actions when the note reveals missing background, competing methods, or follow-up work.
- Link back to the source report with `[[Reports/<object_id>|Title]]`.
- Use Obsidian links to connect related reports, notes, and topics when they help future navigation.
- Keep tags aligned with object metadata; prefer hierarchical tags such as `topic/attention` or `pe/rope`.
- Keep external workflow/status updates in metadata or sync jobs, not in the note body.
- Do not force every note into the same sections.

The CLI may create frontmatter and links, but it must not generate a body template.
