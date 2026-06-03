# Sources Agent Guide

`sources/` stores local source material and snapshots.

Rules:

- `sources/inbox/` is for raw local files before ingestion.
- `sources/pdfs/original/` stores original PDFs.
- `sources/pdfs/annotated/` stores annotated PDFs exported from reading tools.
- `sources/repos/` stores explicitly approved local repository snapshots.
- `sources/web/` stores explicitly approved web snapshots.

Never overwrite original PDFs. Register GitHub repositories and URLs as links first; clone or download only after explicit approval.

Dashboard visibility should reference managed object metadata and vault artifacts, not raw PDFs,
cloned repositories, or web snapshots. Keep source material out of `vault/`.

When an external web clipper is used, treat clipped URLs as intake hints until Codex imports them
into PaC metadata. Do not snapshot web pages, clone repositories, or download files merely because
they appear in an external inbox.
