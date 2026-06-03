# PaC Workspace Agent Guide

This is a private PaC workspace. It contains research notes, reports, metadata, and local source references.

## Workspace Purpose

Use this workspace for daily research-object management. A research object can include PDFs, arXiv links, GitHub repositories, web pages, annotations, implementation references, reports, and deep notes.

## Core Principle

PaC prepares; Codex reasons.

The engine may create files, validate metadata, build context, and index content. It must not mechanically generate evaluations, ratings, or final report prose.

## Privacy Rules

- Keep this workspace private by default.
- Track notes, reports, and YAML metadata.
- Do not commit raw PDFs, annotated PDFs, cloned repositories, web snapshots, generated indexes, `.env`, or local caches.
- Never overwrite original PDFs.

## Optional External Frontend Workflow

External tools such as Notion may be used as a human-facing dashboard while PaC remains the local
metadata and validation engine. A scalable pattern is:

1. External Inbox captures candidate sources.
2. Codex reviews new inbox items, records an import decision, and writes concise feedback.
3. Accepted items become PaC intake/source/object records.
4. Codex writes reports from `templates/report.md` after reading source context.
5. External Research views show human workflow state, ratings, tags, and links back to local
   artifacts when useful.

Keep field ownership clear:

- Human workflow state belongs to the external frontend or object metadata.
- Codex worker state belongs to an explicit Codex status field.
- Last-synced timestamps are audit data, not the only conflict detector.
- A workspace-private sync ledger should remember external page IDs, observed edit timestamps,
  local hashes, sync direction, and conflicts.

## Obsidian

Open only `vault/` in Obsidian.

Use `pac dashboard build --format obsidian --json` to refresh `vault/Dashboard.md`.
Use `pac dashboard build --format html --json` for a browser review page in `indexes/`.
The dashboard reads object metadata, report/note frontmatter, and artifact status; it is not a
place for final report prose.

## Tags and Connections

Store tags and curated related object IDs in `library/objects/*.yaml`. Use lowercase hierarchical
tags without a leading `#`, such as `topic/attention`, `pe/rope`, `model/transformer`,
`method/rag`, `task/long-context`, `system/inference`, and `status/needs-note`.

Use Obsidian wiki links in reports and notes to connect related artifacts. The engine may sync
frontmatter links, but Codex should write body links only after reading context and reasoning about
the relationship.

External frontend tags should map to the same metadata taxonomy. Store tags without a leading `#`
in YAML; render them with `#` only in Markdown text when needed.

## Codex Evaluation Profiles

Use `codex/profiles/` for Markdown instructions that describe the workspace owner's research
interests and evaluation priorities. `pac-workspace.yaml` selects the active profile.

When evaluating a source, combine the selected profile with current workspace context. Consider
existing objects, reports, notes, tags, and available indexes, then recommend related sources as
next actions when the new source reveals a useful topic cluster or missing background.
