# Templates Agent Guide

`templates/` contains workspace-level standards for Codex-authored artifacts.

Templates are instructional contracts, not mechanical generators. The report template defines required report sections, but Codex must still read the research object context and reason before writing content.

Report frontmatter should stay Dataview-friendly and aligned with object metadata: `type`, `object_id`, `title`, `rating`, `status`, `tags`, `related`, and wiki-link fields belong in frontmatter.

When importing from an external frontend, write reports from the report template and preserve the
required headings so `pac report validate` can catch incomplete work. Do not replace the template
with a generated prose outline or a Notion-specific structure.

Do not add a deep-note body template. Deep-note guidance belongs in `vault/Notes/AGENTS.md`.
