# Library Agent Guide

`library/` is the YAML source of truth.

Use:

- `library/intake/` for intake records.
- `library/objects/` for research object records.
- `library/sources/` for source records.

Metadata must be valid YAML and conform to the Pydantic schemas in the PaC engine. Prefer explicit status fields over inferred workflow state. Do not put generated search data here.

Object metadata is authoritative for dashboard behavior:

- `tags` stores lowercase hierarchical tags without leading `#`.
- `related` stores curated related object IDs.
- Ratings and workflow statuses drive dashboard queues.

Vault frontmatter and wiki links should be synced from, or kept consistent with, this metadata.

External sync ledgers may live under `library/sync/` in private workspaces. They are durable sync
memory, unlike `indexes/pac.sqlite`, which is generated and may be rebuilt. If a ledger is used,
keep external page IDs, local hashes, observed edit timestamps, sync direction, Codex status, and
conflict reasons there rather than scattering them across reports.
