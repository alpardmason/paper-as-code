from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from pac.models import (
    Artifacts,
    ImplementationStatus,
    IngestionStatus,
    IntakeRecord,
    IntakeStatus,
    Location,
    NoteStatus,
    Rating,
    ReportStatus,
    ResearchObject,
    SourceKind,
    SourceRecord,
    Workflow,
    utc_now,
)
from pac.paths import REQUIRED_AGENT_FILES, REQUIRED_DIRECTORIES, ProjectPaths
from pac.pdf import extract_pdf_text
from pac.storage import Repository, StorageError, load_model
from pac.utils import (
    LINK_RE,
    copy_without_overwrite,
    detect_source_kind,
    resolve_local_path,
    sha256_file,
    stable_intake_id,
    stable_object_id,
    stable_source_id,
    title_from_id,
)

REPORT_SECTIONS = (
    "## Rating",
    "## One-Sentence Takeaway",
    "## Why This Matters",
    "## Core Idea",
    "## Technical Details",
    "## Evidence and Results",
    "## Limitations and Risks",
    "## Implementation Relevance",
    "## Related Work and Connections",
    "## Recommended Next Actions",
)

TAG_RE = re.compile(
    r"^(?:topic|pe|model|method|task|system|status)"
    r"/[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)*$"
)


class PacError(RuntimeError):
    pass


def model_json(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if isinstance(model, list):
        return [model_json(item) for item in model]
    if isinstance(model, dict):
        return {key: model_json(value) for key, value in model.items()}
    return model


def add_intake(paths: ProjectPaths, *, source: str, kind: str) -> dict[str, Any]:
    repo = Repository(paths)
    source_kind = detect_source_kind(source, kind)
    intake_id = stable_intake_id(source)
    path = repo.intake_path(intake_id)
    created = not path.exists()
    if created:
        repo.save_intake(IntakeRecord(intake_id=intake_id, source=source, kind=source_kind))
    record = repo.load_intake(intake_id)
    return {"ok": True, "created": created, "intake": model_json(record)}


def scan_intake(paths: ProjectPaths) -> dict[str, Any]:
    inbox_dir = paths.root / paths.config.sources_dir / "inbox"
    vault_inbox_dir = paths.root / paths.config.vault_dir / "Inbox"
    files = [
        paths.relative(path)
        for path in sorted(inbox_dir.rglob("*"))
        if path.is_file()
    ]
    links: list[dict[str, str]] = []
    for markdown in sorted(vault_inbox_dir.glob("*.md")):
        text = markdown.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            links.append({"file": paths.relative(markdown), "url": match.group(0)})
    return {"ok": True, "files": files, "links": links}


def list_intakes(paths: ProjectPaths) -> dict[str, Any]:
    records = Repository(paths).list_intakes()
    return {"ok": True, "intakes": model_json(records)}


def ingest_intake(paths: ProjectPaths, *, intake_id: str) -> dict[str, Any]:
    repo = Repository(paths)
    try:
        intake = repo.load_intake(intake_id)
    except FileNotFoundError as exc:
        raise PacError(f"Unknown intake record: {intake_id}") from exc

    if intake.status == IntakeStatus.INGESTED and intake.object_id and intake.source_id:
        return {
            "ok": True,
            "created": [],
            "intake": model_json(intake),
            "next_actions": _next_report_actions(intake.object_id),
        }

    object_id = stable_object_id(intake.source, intake.kind)
    source = _create_source_from_intake(paths, intake, object_id)
    repo.save_source(source)

    object_path = repo.object_path(object_id)
    created: list[str] = [paths.relative(repo.source_path(source.source_id))]
    if object_path.exists():
        research_object = repo.load_object(object_id)
        if source.source_id not in research_object.sources:
            research_object.sources.append(source.source_id)
    else:
        research_object = ResearchObject(
            object_id=object_id,
            title=title_from_id(object_id),
            sources=[source.source_id],
            artifacts=Artifacts(report=paths.relative(paths.report_dir / f"{object_id}.md")),
            workflow=Workflow(
                ingestion_status=IngestionStatus.COMPLETE,
                report_status=ReportStatus.PENDING,
                note_status=NoteStatus.NOT_REQUIRED,
                implementation_status=ImplementationStatus.NOT_APPLICABLE,
            ),
        )
    research_object.workflow.ingestion_status = IngestionStatus.COMPLETE
    research_object.updated_at = utc_now()
    repo.save_object(research_object)
    created.append(paths.relative(repo.object_path(object_id)))

    report_result = ensure_report(paths, object_id=object_id)
    created.extend(report_result.get("created", []))

    intake.status = IntakeStatus.INGESTED
    intake.object_id = object_id
    intake.source_id = source.source_id
    intake.updated_at = utc_now()
    repo.save_intake(intake)

    return {
        "ok": True,
        "object_id": object_id,
        "source_id": source.source_id,
        "created": created,
        "status": {
            "ingestion": "complete",
            "report": research_object.workflow.report_status.value,
            "rating": research_object.rating,
            "note": research_object.workflow.note_status.value,
        },
        "next_actions": _next_report_actions(object_id),
    }


def _create_source_from_intake(
    paths: ProjectPaths, intake: IntakeRecord, object_id: str
) -> SourceRecord:
    source_id = stable_source_id(intake.source, intake.kind)
    metadata: dict[str, Any] = {"registered_from_intake": intake.intake_id}
    if intake.kind == SourceKind.PDF:
        source_path = resolve_local_path(paths, intake.source)
        if not source_path.exists():
            raise PacError(f"PDF source does not exist: {source_path}")
        destination = paths.original_pdfs_dir / f"{object_id}.pdf"
        stored_path, copied = copy_without_overwrite(source_path, destination)
        metadata["copied"] = copied
        return SourceRecord(
            source_id=source_id,
            kind=SourceKind.PDF,
            location=Location(path=paths.relative(stored_path)),
            sha256=sha256_file(stored_path),
            metadata=metadata,
        )
    if intake.kind == SourceKind.GITHUB_REPO:
        metadata["clone_status"] = "not_cloned"
    if intake.kind in {SourceKind.URL, SourceKind.ARXIV}:
        metadata["snapshot_status"] = "not_downloaded"
    return SourceRecord(
        source_id=source_id,
        kind=intake.kind,
        location=Location(url=intake.source),
        metadata=metadata,
    )


def _next_report_actions(object_id: str) -> list[dict[str, str]]:
    return [
        {
            "action": "context_build",
            "command": f"pac context build --id {object_id} --purpose report --json",
        },
        {
            "action": "codex_write_report",
            "target": f"vault/Reports/{object_id}.md",
        },
    ]


def list_objects(paths: ProjectPaths) -> dict[str, Any]:
    objects = Repository(paths).list_objects()
    return {"ok": True, "objects": model_json(objects)}


def show_object(paths: ProjectPaths, *, object_id: str) -> dict[str, Any]:
    return {"ok": True, "object": model_json(_load_object(paths, object_id))}


def update_object(
    paths: ProjectPaths,
    *,
    object_id: str,
    rating: Rating | None = None,
    tags: list[str] | None = None,
    related: list[str] | None = None,
) -> dict[str, Any]:
    repo = Repository(paths)
    research_object = _load_object(paths, object_id)
    if rating is not None:
        research_object.rating = rating
        if rating >= 2 and research_object.workflow.note_status == NoteStatus.NOT_REQUIRED:
            research_object.workflow.note_status = NoteStatus.PENDING
        if rating == 1:
            research_object.workflow.note_status = NoteStatus.NOT_REQUIRED
    if tags is not None:
        research_object.tags = _validate_tags(tags)
    if related is not None:
        research_object.related = _validate_related(repo, object_id, related)
    research_object.updated_at = utc_now()
    repo.save_object(research_object)
    _sync_existing_artifacts(paths, research_object)
    return {"ok": True, "object": model_json(research_object)}


def _validate_tags(tags: list[str]) -> list[str]:
    validated: list[str] = []
    for tag in _dedupe_strings(tags):
        if not TAG_RE.fullmatch(tag):
            raise PacError(
                f"Invalid tag: {tag}. Use lowercase hierarchical tags like topic/attention."
            )
        validated.append(tag)
    return validated


def _validate_related(
    repo: Repository, object_id: str, related_object_ids: list[str]
) -> list[str]:
    validated: list[str] = []
    for related_id in _dedupe_strings(related_object_ids):
        if related_id == object_id:
            raise PacError(f"Research object {object_id} cannot relate object to itself.")
        if not repo.object_path(related_id).exists():
            raise PacError(f"Unknown related object: {related_id}")
        validated.append(related_id)
    return validated


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def ensure_report(paths: ProjectPaths, *, object_id: str) -> dict[str, Any]:
    repo = Repository(paths)
    research_object = _load_object(paths, object_id)
    report_path = paths.root / research_object.artifacts.report
    created: list[str] = []
    if not report_path.exists():
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_report_stub(paths, research_object), encoding="utf-8")
        created.append(paths.relative(report_path))
    research_object.artifacts.report = paths.relative(report_path)
    research_object.workflow.report_status = ReportStatus.PENDING
    research_object.updated_at = utc_now()
    repo.save_object(research_object)
    _sync_artifact_frontmatter(paths, research_object, artifact_kind="report")
    return {"ok": True, "created": created, "report": paths.relative(report_path)}


def _report_stub(paths: ProjectPaths, research_object: ResearchObject) -> str:
    return (
        _frontmatter_block(_artifact_frontmatter(paths, research_object, artifact_kind="report"))
        + "\n"
        "<!-- Codex: generate this report using templates/report.md and "
        f"`pac context build --id {research_object.object_id} --purpose report --json`. -->\n"
    )


def validate_report(paths: ProjectPaths, *, object_id: str) -> dict[str, Any]:
    research_object = _load_object(paths, object_id)
    report_path = paths.root / research_object.artifacts.report
    errors: list[str] = []
    if not report_path.exists():
        return {"ok": False, "errors": [f"Missing report: {research_object.artifacts.report}"]}
    text = report_path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    if frontmatter is None:
        errors.append("Missing YAML frontmatter")
    else:
        if frontmatter.get("object_id") != object_id:
            errors.append("Frontmatter object_id does not match metadata")
        if "title" not in frontmatter:
            errors.append("Frontmatter missing title")
    for section in REPORT_SECTIONS:
        if section not in text:
            errors.append(f"Missing report section: {section}")
    return {"ok": not errors, "errors": errors, "report": paths.relative(report_path)}


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _sync_existing_artifacts(paths: ProjectPaths, research_object: ResearchObject) -> None:
    _sync_artifact_frontmatter(paths, research_object, artifact_kind="report")
    if research_object.artifacts.note:
        _sync_artifact_frontmatter(paths, research_object, artifact_kind="note")


def _sync_artifact_frontmatter(
    paths: ProjectPaths, research_object: ResearchObject, *, artifact_kind: str
) -> None:
    artifact_path = _artifact_path(paths, research_object, artifact_kind=artifact_kind)
    if artifact_path is None or not artifact_path.exists():
        return
    body = _markdown_body(artifact_path.read_text(encoding="utf-8"))
    artifact_path.write_text(
        _frontmatter_block(
            _artifact_frontmatter(paths, research_object, artifact_kind=artifact_kind)
        )
        + body,
        encoding="utf-8",
    )


def _artifact_path(
    paths: ProjectPaths, research_object: ResearchObject, *, artifact_kind: str
) -> Path | None:
    if artifact_kind == "report":
        return paths.root / research_object.artifacts.report
    if artifact_kind == "note" and research_object.artifacts.note:
        return paths.root / research_object.artifacts.note
    return None


def _markdown_body(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            return parts[2]
    return f"\n{text}" if text else "\n"


def _frontmatter_block(frontmatter: dict[str, Any]) -> str:
    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n"


def _artifact_frontmatter(
    paths: ProjectPaths, research_object: ResearchObject, *, artifact_kind: str
) -> dict[str, Any]:
    title = research_object.title or title_from_id(research_object.object_id)
    status = (
        research_object.workflow.report_status.value
        if artifact_kind == "report"
        else research_object.workflow.note_status.value
    )
    frontmatter: dict[str, Any] = {
        "type": artifact_kind,
        "object_id": research_object.object_id,
        "title": title,
        "rating": research_object.rating,
        "status": status,
        "tags": research_object.tags,
        "related": research_object.related,
        "related_reports": _related_wiki_links(
            paths, research_object, artifact_kind="report"
        ),
        "related_notes": _related_wiki_links(paths, research_object, artifact_kind="note"),
    }
    if artifact_kind == "report":
        frontmatter["note"] = _artifact_wiki_link(paths, research_object, artifact_kind="note")
    else:
        frontmatter["report"] = _artifact_wiki_link(
            paths, research_object, artifact_kind="report"
        )
    return frontmatter


def _related_wiki_links(
    paths: ProjectPaths, research_object: ResearchObject, *, artifact_kind: str
) -> list[str]:
    repo = Repository(paths)
    links: list[str] = []
    for related_id in research_object.related:
        try:
            related_object = repo.load_object(related_id)
        except FileNotFoundError:
            continue
        link = _artifact_wiki_link(paths, related_object, artifact_kind=artifact_kind)
        if link is not None:
            links.append(link)
    return links


def _artifact_wiki_link(
    paths: ProjectPaths, research_object: ResearchObject, *, artifact_kind: str
) -> str | None:
    artifact = (
        research_object.artifacts.report
        if artifact_kind == "report"
        else research_object.artifacts.note
    )
    if artifact is None:
        return None
    target = _vault_wiki_target(paths, artifact)
    title = research_object.title or title_from_id(research_object.object_id)
    return _wiki_link(target, title)


def _vault_wiki_target(paths: ProjectPaths, artifact: str) -> str:
    artifact_path = Path(artifact)
    try:
        target = artifact_path.relative_to(paths.config.vault_dir)
    except ValueError:
        target = artifact_path
    return target.with_suffix("").as_posix()


def _wiki_link(target: str, title: str) -> str:
    alias = " ".join(title.replace("|", " ").split())
    return f"[[{target}|{alias}]]"


def ensure_note(paths: ProjectPaths, *, object_id: str) -> dict[str, Any]:
    repo = Repository(paths)
    research_object = _load_object(paths, object_id)
    if research_object.rating not in {2, 3}:
        research_object.workflow.note_status = NoteStatus.NOT_REQUIRED
        research_object.updated_at = utc_now()
        repo.save_object(research_object)
        return {
            "ok": False,
            "reason": "Deep notes are only required for rating 2 or 3 objects.",
            "note_status": research_object.workflow.note_status.value,
        }

    note_path = paths.notes_dir / f"{object_id}.md"
    created: list[str] = []
    if not note_path.exists():
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(_note_stub(paths, research_object), encoding="utf-8")
        created.append(paths.relative(note_path))
    research_object.artifacts.note = paths.relative(note_path)
    if research_object.workflow.note_status == NoteStatus.NOT_REQUIRED:
        research_object.workflow.note_status = NoteStatus.PENDING
    research_object.updated_at = utc_now()
    repo.save_object(research_object)
    _sync_artifact_frontmatter(paths, research_object, artifact_kind="note")
    _sync_artifact_frontmatter(paths, research_object, artifact_kind="report")
    return {"ok": True, "created": created, "note": paths.relative(note_path)}


def _note_stub(paths: ProjectPaths, research_object: ResearchObject) -> str:
    return (
        _frontmatter_block(_artifact_frontmatter(paths, research_object, artifact_kind="note"))
        + "\n"
        "<!-- Codex: write this flexible deep note according to vault/Notes/AGENTS.md "
        "and the user's prompt. -->\n"
    )


def import_annotation(paths: ProjectPaths, *, object_id: str, source: str) -> dict[str, Any]:
    repo = Repository(paths)
    research_object = _load_object(paths, object_id)
    source_path = resolve_local_path(paths, source)
    if not source_path.exists():
        raise PacError(f"Annotated PDF does not exist: {source_path}")
    destination = paths.annotated_pdfs_dir / f"{object_id}.annotated.pdf"
    stored_path, copied = copy_without_overwrite(source_path, destination)
    source_id = stable_source_id(str(stored_path), SourceKind.ANNOTATED_PDF)
    source_record = SourceRecord(
        source_id=source_id,
        kind=SourceKind.ANNOTATED_PDF,
        location=Location(path=paths.relative(stored_path)),
        sha256=sha256_file(stored_path),
        metadata={"copied": copied},
    )
    repo.save_source(source_record)
    if source_id not in research_object.sources:
        research_object.sources.append(source_id)
    research_object.updated_at = utc_now()
    repo.save_object(research_object)
    return {
        "ok": True,
        "source_id": source_id,
        "stored_path": paths.relative(stored_path),
        "copied": copied,
    }


def attach_implementation(paths: ProjectPaths, *, object_id: str, repo_path: str) -> dict[str, Any]:
    repo = Repository(paths)
    research_object = _load_object(paths, object_id)
    path = Path(repo_path).expanduser()
    source_id = stable_source_id(repo_path, SourceKind.IMPLEMENTATION_REPO)
    source_record = SourceRecord(
        source_id=source_id,
        kind=SourceKind.IMPLEMENTATION_REPO,
        location=Location(path=str(path)),
        metadata={"exists": path.exists()},
    )
    repo.save_source(source_record)
    if source_id not in research_object.sources:
        research_object.sources.append(source_id)
    research_object.workflow.implementation_status = ImplementationStatus.ATTACHED
    research_object.updated_at = utc_now()
    repo.save_object(research_object)
    return {
        "ok": True,
        "source_id": source_id,
        "implementation_status": research_object.workflow.implementation_status.value,
        "warning": None if path.exists() else "Repository path was registered but does not exist.",
    }


def build_context(paths: ProjectPaths, *, object_id: str, purpose: str) -> dict[str, Any]:
    repo = Repository(paths)
    research_object = _load_object(paths, object_id)
    sources = [_load_source(paths, source_id) for source_id in research_object.sources]
    source_payloads: list[dict[str, Any]] = []
    for source in sources:
        payload = source.model_dump(mode="json")
        if source.location.path and source.kind in {SourceKind.PDF, SourceKind.ANNOTATED_PDF}:
            source_path = paths.root / source.location.path
            extracted_path = _ensure_extracted_text(paths, source.source_id, source_path)
            payload["extracted_text"] = paths.relative(extracted_path) if extracted_path else None
        source_payloads.append(payload)

    payload = {
        "ok": True,
        "object_id": object_id,
        "purpose": purpose,
        "metadata_file": paths.relative(repo.object_path(object_id)),
        "template_file": paths.relative(paths.report_template) if purpose == "report" else None,
        "report_file": research_object.artifacts.report,
        "note_file": research_object.artifacts.note,
        "sources": source_payloads,
        "codex": _codex_context(paths),
        "instructions": _context_instructions(purpose),
    }
    context_dir = paths.indexes_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    output_path = context_dir / f"{object_id}.{purpose}.yaml"
    output_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    payload["context_file"] = paths.relative(output_path)
    return payload


def _codex_context(paths: ProjectPaths) -> dict[str, Any]:
    codex = paths.config.codex
    warnings: list[str] = []
    profile_text: str | None = None
    if codex.evaluation_profile_file:
        profile_path = paths.root / codex.evaluation_profile_file
        if not profile_path.exists():
            warnings.append(
                f"Codex evaluation profile file is missing: {codex.evaluation_profile_file}"
            )
        elif not profile_path.is_file():
            warnings.append(
                f"Codex evaluation profile path is not a file: {codex.evaluation_profile_file}"
            )
        else:
            try:
                profile_text = profile_path.read_text(encoding="utf-8")
            except OSError as exc:
                warnings.append(
                    "Codex evaluation profile file could not be read: "
                    f"{codex.evaluation_profile_file}: {exc}"
                )
    return {
        "evaluation_profile": codex.evaluation_profile,
        "evaluation_profile_file": codex.evaluation_profile_file,
        "evaluation_profile_text": profile_text,
        "interests": codex.interests,
        "warnings": warnings,
    }


def _context_instructions(purpose: str) -> list[str]:
    if purpose == "report":
        return [
            "Read the source context and templates/report.md.",
            "Apply the workspace Codex evaluation profile when present.",
            "Write a standardized report in vault/Reports.",
            "Do not invent a rating before evaluating usefulness.",
        ]
    if purpose == "note":
        return [
            "Read vault/Notes/AGENTS.md and the user's prompt.",
            "Write a flexible deep note rather than filling a body template.",
            "Merge reports, annotations, and implementation insights when available.",
        ]
    return [
        "Inspect attached implementation context.",
        "Summarize implementation lessons for merging into the deep note.",
    ]


def _ensure_extracted_text(paths: ProjectPaths, source_id: str, pdf_path: Path) -> Path | None:
    if not pdf_path.exists():
        return None
    output = paths.indexes_dir / "extracted" / f"{source_id}.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        output.write_text(extract_pdf_text(pdf_path), encoding="utf-8")
    return output


def doctor(paths: ProjectPaths) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    for directory in REQUIRED_DIRECTORIES:
        if not paths.rel(directory).is_dir():
            issues.append({"severity": "error", "message": f"Missing directory: {directory}"})
    for agent_file in REQUIRED_AGENT_FILES:
        if not paths.rel(agent_file).is_file():
            issues.append({"severity": "warning", "message": f"Missing AGENTS file: {agent_file}"})

    repo = Repository(paths)
    for path in sorted(paths.intake_dir.glob("*.yaml")):
        try:
            load_model(path, IntakeRecord)
        except (StorageError, ValueError) as exc:
            issues.append({"severity": "error", "message": str(exc)})
    for path in sorted(paths.sources_dir.glob("*.yaml")):
        try:
            load_model(path, SourceRecord)
        except (StorageError, ValueError) as exc:
            issues.append({"severity": "error", "message": str(exc)})
    for path in sorted(paths.objects_dir.glob("*.yaml")):
        try:
            load_model(path, ResearchObject)
        except (StorageError, ValueError) as exc:
            issues.append({"severity": "error", "message": str(exc)})

    for research_object in _safe_list_objects(repo, issues):
        report_path = paths.root / research_object.artifacts.report
        if not report_path.exists():
            message = (
                f"Missing report for {research_object.object_id}: "
                f"{research_object.artifacts.report}"
            )
            issues.append({
                "severity": "warning",
                "message": message,
            })
        if research_object.artifacts.note:
            note_path = paths.root / research_object.artifacts.note
            if not note_path.exists():
                message = (
                    f"Missing note for {research_object.object_id}: "
                    f"{research_object.artifacts.note}"
                )
                issues.append({
                    "severity": "warning",
                    "message": message,
                })
        for source_id in research_object.sources:
            source_file = repo.source_path(source_id)
            if not source_file.exists():
                message = f"Missing source metadata {source_id} for {research_object.object_id}"
                issues.append({
                    "severity": "error",
                    "message": message,
                })

    for source in _safe_list_sources(repo, issues):
        if source.location.path and source.kind != SourceKind.IMPLEMENTATION_REPO:
            source_path = paths.root / source.location.path
            if not source_path.exists():
                message = f"Missing source file for {source.source_id}: {source.location.path}"
                issues.append({
                    "severity": "error",
                    "message": message,
                })

    return {"ok": not any(issue["severity"] == "error" for issue in issues), "issues": issues}


def status(paths: ProjectPaths) -> dict[str, Any]:
    repo = Repository(paths)
    objects = repo.list_objects()
    ratings = Counter(str(item.rating) if item.rating else "unset" for item in objects)
    report_statuses = Counter(item.workflow.report_status.value for item in objects)
    note_statuses = Counter(item.workflow.note_status.value for item in objects)
    pending_reports = [
        item.object_id
        for item in objects
        if item.workflow.report_status in {ReportStatus.PENDING, ReportStatus.DRAFT}
    ]
    notes_needed = [
        item.object_id
        for item in objects
        if item.rating in {2, 3} and item.workflow.note_status != NoteStatus.COMPLETE
    ]
    return {
        "ok": True,
        "counts": {
            "intakes": len(repo.list_intakes()),
            "objects": len(objects),
            "sources": len(repo.list_sources()),
            "ratings": dict(ratings),
            "report_statuses": dict(report_statuses),
            "note_statuses": dict(note_statuses),
        },
        "next_actions": {
            "pending_reports": pending_reports,
            "notes_needed": notes_needed,
        },
    }


def _safe_list_objects(repo: Repository, issues: list[dict[str, str]]) -> list[ResearchObject]:
    try:
        return repo.list_objects()
    except StorageError as exc:
        issues.append({"severity": "error", "message": str(exc)})
        return []


def _safe_list_sources(repo: Repository, issues: list[dict[str, str]]) -> list[SourceRecord]:
    try:
        return repo.list_sources()
    except StorageError as exc:
        issues.append({"severity": "error", "message": str(exc)})
        return []


def _load_object(paths: ProjectPaths, object_id: str) -> ResearchObject:
    try:
        return Repository(paths).load_object(object_id)
    except FileNotFoundError as exc:
        raise PacError(f"Unknown research object: {object_id}") from exc


def _load_source(paths: ProjectPaths, source_id: str) -> SourceRecord:
    try:
        return Repository(paths).load_source(source_id)
    except FileNotFoundError as exc:
        raise PacError(f"Unknown source: {source_id}") from exc
