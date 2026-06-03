from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pac.models import SourceKind
from pac.paths import ProjectPaths
from pac.pdf import extract_pdf_text
from pac.services import model_json
from pac.storage import Repository


def rebuild_index(paths: ProjectPaths) -> dict[str, Any]:
    repo = Repository(paths)
    paths.indexes_dir.mkdir(parents=True, exist_ok=True)
    db_path = paths.indexes_dir / "pac.sqlite"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE search USING fts5("
            "object_id, kind, path, title, content)"
        )
        docs_indexed = 0
        for research_object in repo.list_objects():
            object_content = json.dumps(model_json(research_object), ensure_ascii=False)
            _insert(
                connection,
                research_object.object_id,
                "metadata",
                f"library/objects/{research_object.object_id}.yaml",
                research_object.title or research_object.object_id,
                object_content,
            )
            docs_indexed += 1

            for artifact_kind, artifact_path in (
                ("report", research_object.artifacts.report),
                ("note", research_object.artifacts.note),
            ):
                if artifact_path:
                    path = paths.root / artifact_path
                    if path.exists():
                        _insert(
                            connection,
                            research_object.object_id,
                            artifact_kind,
                            artifact_path,
                            research_object.title or research_object.object_id,
                            path.read_text(encoding="utf-8"),
                        )
                        docs_indexed += 1

            for source_id in research_object.sources:
                source = repo.load_source(source_id)
                content = json.dumps(model_json(source), ensure_ascii=False)
                source_path = source.location.path
                if source_path and source.kind in {SourceKind.PDF, SourceKind.ANNOTATED_PDF}:
                    pdf_path = paths.root / source_path
                    extracted_path = _write_extracted_pdf_text(paths, source_id, pdf_path)
                    if extracted_path.exists():
                        content = extracted_path.read_text(encoding="utf-8")
                        source_path = paths.relative(extracted_path)
                _insert(
                    connection,
                    research_object.object_id,
                    source.kind.value,
                    source_path or source.location.url or source.source_id,
                    research_object.title or research_object.object_id,
                    content,
                )
                docs_indexed += 1
        connection.commit()
    finally:
        connection.close()

    context_path = _write_codex_context(paths)
    return {
        "ok": True,
        "database": paths.relative(db_path),
        "codex_context": paths.relative(context_path),
        "documents_indexed": docs_indexed,
    }


def search(paths: ProjectPaths, query: str) -> dict[str, Any]:
    db_path = paths.indexes_dir / "pac.sqlite"
    if not db_path.exists():
        return {
            "ok": False,
            "error": "Search index does not exist. Run `pac index rebuild --json` first.",
            "results": [],
        }
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        try:
            rows = connection.execute(
                "SELECT object_id, kind, path, title, snippet(search, 4, '[', ']', '...', 16) "
                "AS snippet FROM search WHERE search MATCH ? LIMIT 20",
                (query,),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = connection.execute(
                "SELECT object_id, kind, path, title, substr(content, 1, 240) AS snippet "
                "FROM search WHERE content LIKE '%' || ? || '%' LIMIT 20",
                (query,),
            ).fetchall()
    finally:
        connection.close()
    return {"ok": True, "results": [dict(row) for row in rows]}


def _insert(
    connection: sqlite3.Connection,
    object_id: str,
    kind: str,
    path: str,
    title: str,
    content: str,
) -> None:
    connection.execute(
        "INSERT INTO search (object_id, kind, path, title, content) VALUES (?, ?, ?, ?, ?)",
        (object_id, kind, path, title, content),
    )


def _write_extracted_pdf_text(paths: ProjectPaths, source_id: str, pdf_path: Path) -> Path:
    output = paths.indexes_dir / "extracted" / f"{source_id}.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists() and not output.exists():
        output.write_text(extract_pdf_text(pdf_path), encoding="utf-8")
    return output


def _write_codex_context(paths: ProjectPaths) -> Path:
    repo = Repository(paths)
    lines = ["# PaC Codex Context", ""]
    for research_object in repo.list_objects():
        rating = research_object.rating if research_object.rating else "unset"
        title = research_object.title or research_object.object_id
        lines.append(
            f"- `{research_object.object_id}`: {title} "
            f"(rating: {rating}, report: {research_object.workflow.report_status.value}, "
            f"note: {research_object.workflow.note_status.value})"
        )
    output = paths.indexes_dir / "codex-context.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
