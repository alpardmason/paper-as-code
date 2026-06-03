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

## Obsidian

Open only `vault/` in Obsidian.

## Codex Evaluation Profiles

Use `codex/profiles/` for Markdown instructions that describe the workspace owner's research
interests and evaluation priorities. `pac-workspace.yaml` selects the active profile.

When evaluating a source, combine the selected profile with current workspace context. Consider
existing objects, reports, notes, tags, and available indexes, then recommend related sources as
next actions when the new source reveals a useful topic cluster or missing background.
