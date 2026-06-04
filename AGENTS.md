# PaC Engine Agent Guide

## Project Purpose

This repository is the public PaC engine. It provides a local-first Paper as Code CLI, schemas, default workspace assets, tests, and documentation for research engineering workflows.

Private research data belongs in a separate PaC workspace, not in this repository.

## Architecture

- `src/` holds the Python CLI implementation.
- `src/pac/assets/workspace_template/` holds reusable private-workspace defaults.
- `tests/` holds pytest coverage.
- `docs/` holds public engine documentation.

## Core Principle

PaC prepares; Codex reasons.

The engine may create workspace files, validate metadata, build context, and index content. It must not mechanically generate evaluations, ratings, or final report prose. Reports and deep notes must come from Codex reading the available context and reasoning about it.

## Agent-First CLI Expectations

- Prefer deterministic, idempotent commands.
- Every command must support JSON output.
- Avoid interactive prompts in CLI behavior.
- Use explicit approval flags before network downloads, GitHub cloning, overwrites, or other persistent external actions.
- Treat nonzero exits as operational failures, not ordinary review outcomes.
- Return validation results as structured data.
- Resolve workspaces through `--workspace`, `PAC_WORKSPACE`, or nearest `pac-workspace.yaml`.
- If none of those are available, resolve through engine config `default_workspace`.
- Keep dashboard commands deterministic: build dashboard data from workspace metadata, emit JSON,
  and write rendered Obsidian/HTML views only for explicit dashboard commands.

## Optional External Frontends

PaC may document generic external frontends, such as Notion, as private-workspace workflows. The
public engine must stay connector-agnostic until a tested generic sync API exists.

Rules:

- Do not add hard-coded Notion database IDs, page IDs, private URLs, private workspace paths, or
  personal source names to public engine files.
- Treat external frontend metadata as workspace-private configuration or ledger state.
- Keep external sync guidance generic: field names and ownership rules are acceptable; real IDs and
  personal examples are not.
- External frontend syncs must use an exact durable decision field or ledger state for item
  processing; semantic search results are not a completeness guarantee.
- External frontend syncs must check for an existing object/page by stable object ID, source URL,
  or exact title before creating a new frontend row. Duplicate stable IDs are conflicts, not normal
  sync results.
- Keep durable sync ledgers separate from generated search indexes such as `indexes/pac.sqlite`.
- Codex-authored reports must use `templates/report.md`; PaC must not generate final report prose
  or deep-note prose during sync.

## Engineering Standards

- Use Python 3.12 and `uv`.
- Prefer correctness, readability, and maintainability over performance.
- Use Pydantic models for structured metadata.
- Use `pathlib.Path` for paths.
- Add or update tests before changing behavior.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy src` before considering implementation complete.

## Source Safety

- Do not commit private workspace data to the engine repository.
- Keep private workspace directory names out of committed `.gitignore`; ignore local private workspaces through `.git/info/exclude`.
- Before copying guidance from a private workspace into engine defaults or examples, check for personal interests, private paths, unpublished notes, credentials, source names, and other leakage; generalize or omit private details.
- For critical project workflow updates, update the local private workspace and reusable workspace template/example together when applicable, after the leakage check.
- Never overwrite original PDFs.
- Store annotated PDFs separately from originals.
- Register GitHub repositories as links first; clone only after explicit approval.
- Register URLs first; snapshot or download only after explicit approval.
- Treat `library/objects/*.yaml` as the source of truth for tags and related object IDs.
- Treat vault wiki links as readable navigation generated from, or curated alongside, metadata.

## Knowledge Accumulation

Maintain this file with:

- Project tech stack and environment configuration.
- Common errors and pitfalls, including symptom, root cause, fix, and prevention.
- Key technical decisions, including decision, context, alternatives considered, and rationale.

## Tech Stack

- Python 3.12
- `uv`
- `argparse`
- Pydantic
- PyYAML
- pypdf
- SQLite FTS5
- pytest
- ruff
- mypy

## Key Decisions

- Decision: PaC is standalone and exposes only `vault/` to Obsidian.
  Context: Opening the engine project in Obsidian would pollute the vault with code and generated files.
  Alternatives considered: Obsidian-first vault, external vault symlink, whole-repo vault.
  Rationale: A private workspace gives Codex reliable metadata and workflow state while preserving a clean reading UI.

- Decision: Reports are standardized, but deep notes are flexible.
  Context: Reports need comparability; notes need freedom for different research objects and prompts.
  Alternatives considered: Templates for both reports and notes, no templates.
  Rationale: `templates/report.md` standardizes evaluations, while `vault/Notes/AGENTS.md` guides flexible synthesis.

- Decision: The CLI is an agent API.
  Context: Codex is the primary operator of PaC workflows.
  Alternatives considered: Human-first CLI, Python library only, MCP server first.
  Rationale: JSON-first deterministic commands are easier for agents to inspect, validate, and compose.

- Decision: Split public engine from private workspace.
  Context: Public sharing and daily research use have different privacy boundaries.
  Alternatives considered: Two remotes for one repo, private-only repo, sanitized public export.
  Rationale: Separating reusable software from private notes and sources prevents accidental leakage by design.

- Decision: Use two-level configuration with Markdown Codex evaluation profiles.
  Context: PaC needs user-local defaults while workspaces need portable research preferences.
  Alternatives considered: all config in `pac-workspace.yaml`, committed engine `config.yaml`, AGENTS-only instructions.
  Rationale: Built-in defaults plus optional user-local engine config keep personal paths out of the public repo, while workspace YAML can select readable Markdown profiles for Codex evaluation.

- Decision: License the public engine under MIT.
  Context: PaC is a simple public engine where adoption and reuse matter more than restricting commercial use.
  Alternatives considered: PolyForm Noncommercial, Apache-2.0, Business Source License.
  Rationale: MIT is familiar, permissive, and low-friction for users who can already rebuild similar tooling with coding agents.

- Decision: Use a hybrid dashboard and knowledge graph.
  Context: Reports and notes need a centralized review surface while staying native to Obsidian.
  Alternatives considered: Obsidian + Dataview only, engine-generated HTML only, hybrid dashboard.
  Rationale: `vault/Dashboard.md` gives the daily Obsidian view, while `indexes/dashboard.html`
  provides a portable browser view from the same metadata. Tags and related IDs stay in object
  YAML; report and note frontmatter exposes wiki links for the vault graph.

- Decision: Keep Notion-as-frontend sync private and generic for now.
  Context: A Notion database can be an excellent human review surface, while PaC remains the local
  metadata, report, validation, and indexing engine.
  Alternatives considered: implement `pac notion` immediately, use only Obsidian dashboards, or
  rely on ad hoc Notion scripts.
  Rationale: Private runbooks and ledgers allow experimentation without leaking workspace details
  or freezing a public API before the workflow is stable.
