# Tests Agent Guide

`tests/` contains pytest coverage for PaC behavior.

Test priorities:

- JSON output shape for CLI commands.
- Safe source ingestion.
- No automatic report prose or ratings.
- Stable filename-safe object IDs.
- Report validation.
- Flexible note creation.
- Approval-gated external actions.
- Doctor diagnostics.
- SQLite index rebuild and search.
- Dashboard JSON, Obsidian Markdown, and HTML output.
- Tag taxonomy validation and replace-style tag updates.
- Related object validation, including missing IDs and self-links.
- Report and note frontmatter sync with body preservation.
- Future generic external-sync configuration without private IDs or user paths.
- Sync-ledger schema and migration behavior separate from generated search indexes.
- External status mapping, conflict detection, and audit timestamp handling.
- Report-template discipline for imported objects.
- Leakage checks for public fixtures and documentation.

Use focused fixtures and avoid relying on the user's real local paper library.
