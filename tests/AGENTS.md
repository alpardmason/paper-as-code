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

Use focused fixtures and avoid relying on the user's real local paper library.
