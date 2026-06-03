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
