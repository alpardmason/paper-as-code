# Source Code Agent Guide

`src/` contains the PaC Python implementation.

Code standards:

- Python 3.12.
- Public functions and methods must be typed.
- Use `pathlib.Path`.
- Keep CLI handlers thin and move behavior into tested functions.
- Use Pydantic models for metadata validation.
- Return structured results that are easy to serialize as JSON.

The CLI is an agent API. Avoid hidden side effects and interactive prompts.

Dashboard and graph behavior:

- Keep dashboard CLI handlers thin; gather data and render views in tested service modules.
- Build dashboards from `library/` metadata, not by scraping report prose.
- Preserve report and note bodies when syncing YAML frontmatter.
- Validate tags and related object IDs before saving metadata.
- Do not infer semantic connections mechanically; expose curated `related` metadata and links.
- Every dashboard command must support JSON output and report written paths deterministically.

External sync behavior:

- Do not add a public `pac notion` command until the sync contract, tests, and privacy boundaries
  are explicit.
- Future sync code must be generic and configuration-driven; never embed private database IDs,
  page IDs, workspace paths, source names, or user-specific URLs.
- Sync commands must be deterministic, non-interactive, JSON-first, and safe to run in scheduled
  automation.
- Network access, schema mutation, page mutation, and destructive local writes must be explicit in
  command behavior and covered by tests.
- Store durable sync memory in a workspace-private ledger, not in generated indexes such as
  `indexes/pac.sqlite`, which can be rebuilt at any time.
- Preserve report and note bodies; sync code may align frontmatter and metadata but must not write
  final report prose or deep-note prose.
