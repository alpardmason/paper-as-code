# PaC Engine

PaC is a local-first Paper as Code engine for research engineering.

It manages research objects rather than only papers. A research object can include PDFs, arXiv links, GitHub repositories, web pages, annotations, implementation references, reports, and deep notes.

This repository is the reusable public engine. Personal research data belongs in a separate private PaC workspace.

## Core Principle

PaC prepares; Codex reasons.

The CLI prepares metadata, source files, report stubs, context bundles, and indexes. Codex writes evaluations, ratings, and deep notes after reading the context.

## Engine Layout

```text
src/
tests/
docs/
src/pac/assets/workspace_template/
```

## Create a Private Workspace

```bash
uv run pac workspace init pac-workspace --json
cd pac-workspace
uv sync
uv run pac workspace doctor --json
```

Open only `vault/` from the private workspace in Obsidian.

Private workspaces can also use external frontends such as Notion for review and capture. Keep that
sync configuration and any page/database IDs in the private workspace; the public engine does not
ship a Notion connector yet.

## Development

```bash
uv venv --python 3.12
uv run pytest
uv run ruff check .
uv run mypy src
```

## Common Commands

```bash
uv run pac config show --scope engine --json
uv run pac config set --scope engine default_workspace pac-workspace --json
uv run pac --workspace pac-workspace workspace info --json
uv run pac --workspace pac-workspace intake add --source sources/inbox/paper.pdf --json
uv run pac --workspace pac-workspace intake ingest --id intake-... --json
uv run pac --workspace pac-workspace context build --id 2025-example-paper --purpose report --json
uv run pac --workspace pac-workspace report validate --id 2025-example-paper --json
uv run pac --workspace pac-workspace dashboard build --format obsidian --json
uv run pac --workspace pac-workspace dashboard build --format html --json
uv run pac --workspace pac-workspace index rebuild --json
uv run pac --workspace pac-workspace search "retrieval" --json
```

## Configuration

PaC uses optional user-local engine config plus workspace-local config.

- Engine config path: `PAC_CONFIG` or `${XDG_CONFIG_HOME:-~/.config}/pac/config.yaml`
- Workspace config path: `<workspace>/pac-workspace.yaml`
- Example engine config: `config.yaml.example`

Workspace config can select a Markdown Codex evaluation profile, such as
`codex/profiles/default.md`. Context bundles include that profile so Codex can evaluate sources
according to the workspace owner's interests.

## License

PaC is released under the MIT License. See `LICENSE`.
