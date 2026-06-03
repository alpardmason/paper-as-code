# PaC Engine and Workspace Architecture

PaC is split into two parts:

- **Public engine**: reusable package, CLI, schemas, default workspace assets, docs, and tests.
- **Private workspace**: personal vault, reports, notes, YAML metadata, local source references, and generated indexes.

The engine is safe to publish. The workspace is private by default.

## Workspace Discovery

Commands resolve a workspace in this order:

1. `--workspace <path>`
2. `PAC_WORKSPACE`
3. nearest parent containing `pac-workspace.yaml`
4. engine config `default_workspace`

`--root` remains as a deprecated alias for `--workspace`.

## Configuration

PaC has two configuration levels:

- **Engine config**: optional user-local YAML at `PAC_CONFIG` or
  `${XDG_CONFIG_HOME:-~/.config}/pac/config.yaml`.
- **Workspace config**: `pac-workspace.yaml` inside a workspace.

The engine config is allowed to be missing. Missing engine config uses built-in defaults. The
public engine repo includes `config.yaml.example`, but real `config.yaml` files should stay
untracked because `default_workspace` can expose personal paths.

Workspace config may reference Markdown Codex evaluation profiles. PaC includes the selected
profile in context bundles; Codex performs the actual evaluation and rating.

## Workspace Creation

```bash
pac workspace init pac-workspace --json
```

The command copies only workspace defaults from packaged engine assets. It does not copy engine source code into the workspace.

For the recommended nested layout, keep `pac-workspace/` inside the public engine directory and ignore it from the engine repository. The nested workspace can still be initialized as its own independent private Git repository.

## Dashboard

PaC uses a hybrid dashboard:

- `pac dashboard build --format obsidian --json` writes `vault/Dashboard.md` for Obsidian review.
- `pac dashboard build --format html --json` writes `indexes/dashboard.html` for browser review.

Both views are rendered from the same object metadata, report/note frontmatter, tags, and curated
related object IDs.

## External Frontends

Private workspaces may use external frontends such as Notion for human review while PaC remains the
local metadata, report, validation, and indexing engine.

Recommended generic flow:

1. An external Inbox captures candidate sources.
2. Codex reviews new items and records `Import`, `Skip`, or `Ask Me` decisions.
3. Accepted items become local PaC intake/source/object metadata.
4. Codex writes reports from `templates/report.md`.
5. A private sync ledger records external page IDs, observed edit timestamps, local hashes, sync
   direction, worker status, and conflicts.

The public engine does not include a Notion connector yet. Public code and docs must not contain
private database IDs, page IDs, workspace paths, or personal source names.

## Reliability Design

External frontends are useful, but they make reliability harder because there are two mutable
systems: the local workspace and the remote database. PaC treats that as a sync problem rather than
as a dashboard-rendering problem.

Recommended reliability pattern:

- **Local metadata is authoritative for PaC state**: object IDs, source IDs, tags, related objects,
  report paths, and validation status live in YAML and are checked by the engine.
- **The external frontend owns human workflow state**: fields such as reading readiness,
  review status, human rating, quick notes, and import decisions are optimized for a human UI.
- **Codex worker state is explicit**: a separate worker-status field should say whether the agent
  is synced, importing, blocked, needs review, or in conflict.
- **Audit timestamps are not conflict detectors by themselves**: `Last Synced At` is useful for
  humans, but conflict detection should rely on a ledger with observed remote edit timestamps and
  local content hashes.
- **Generated indexes are disposable**: search indexes and dashboard renderings can be rebuilt and
  must not store durable sync memory.
- **Report prose is guarded by templates and validation**: the engine can create stubs, metadata,
  and context; Codex writes reports only after reading source context and must preserve required
  report headings.

The most important design choice is to keep durable sync memory separate from generated indexes.
A workspace-private SQLite ledger can store external page IDs, source URLs, local metadata hashes,
report hashes, observed remote edit timestamps, sync direction, worker status, and conflict reasons.
That ledger gives Codex a compact operational memory without turning the public engine into a
private data store.

## Harness Engineering

The workflow is easier for agents when the harness is explicit. A good harness has four layers:

1. **Project instructions**: `AGENTS.md` files define privacy boundaries, source safety, report
   discipline, and local directory responsibilities.
2. **Runbook**: a private workflow document describes the exact daily operation, field ownership,
   conflict policy, validation commands, and git working-log convention.
3. **Scheduled prompt**: the automation prompt should be short. It should point to the runbook,
   identify the public engine and private workspace roles, and repeat only the highest-risk
   guardrails.
4. **Validation commands**: every run should end with structured status checks, targeted report
   validation, index rebuild smoke tests when useful, sync-ledger integrity checks, and git status
   inspection.

This structure makes the automation less dependent on one large prompt. The prompt wakes Codex up;
the runbook and AGENTS files supply the contract; the CLI and ledger provide machine-checkable
state. That division is more reliable than asking the model to remember all workflow rules from a
single scheduled message.

For model selection, medium reasoning is a reasonable default for routine sync when the harness is
strong: most work is inspection, filtered reads, metadata updates, report drafting from a template,
and validation. Higher reasoning is better reserved for large conflict resolution, dense technical
reports, or broad architecture changes.

## Token Efficiency

Two-way sync can become expensive if the agent repeatedly reads every report, every remote page, or
every generated index. PaC's token-efficient sync strategy is ledger-first and change-driven.

Recommended token strategy:

- Query the external Inbox with a narrow filter such as `Status = New`; do not scan imported or
  archived intake.
- Use stored external page IDs for updates and relations. Fall back to title or URL search only
  when an ID is missing or stale.
- Compare remote edit timestamps and local hashes before reading full page bodies or report prose.
- Read local YAML metadata before Markdown bodies; read report bodies only when creating,
  validating, changing, or resolving a conflict for that report.
- On a fresh empty ledger, do not backfill the entire remote Research database unless the user asks
  for a full reconciliation. Start with new Inbox items and ledger-known pages.
- Keep generated indexes out of the model context unless the task specifically needs search
  results or context bundles.
- Summarize run results by counts, changed object IDs, validation outcomes, conflicts, commit hash,
  and push status rather than restating unchanged metadata.

The open-source engine should eventually encode these practices as deterministic sync primitives:
filtered remote queries, hash comparison, ledger migrations, conflict classification, and JSON
summaries. Until then, private runbooks and scheduled prompts can guide Codex to behave
efficiently.

## Privacy Boundary

Track in the private workspace:

- `AGENTS.md`
- `pac-workspace.yaml`
- `codex/profiles/`
- `pyproject.toml`
- `vault/`
- `library/`
- `templates/`

Ignore in the private workspace:

- raw PDFs and annotated PDFs
- cloned repositories
- web snapshots
- generated indexes
- caches
- secrets
