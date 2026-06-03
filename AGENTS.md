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
