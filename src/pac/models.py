from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1


def utc_now() -> datetime:
    """Return a stable UTC timestamp without microseconds for metadata files."""
    return datetime.now(tz=UTC).replace(microsecond=0)


Rating = Literal[1, 2, 3]


class SourceKind(StrEnum):
    PDF = "pdf"
    ANNOTATED_PDF = "annotated_pdf"
    ARXIV = "arxiv"
    URL = "url"
    GITHUB_REPO = "github_repo"
    WEB_SNAPSHOT = "web_snapshot"
    IMPLEMENTATION_REPO = "implementation_repo"


class IntakeStatus(StrEnum):
    PENDING = "pending"
    INGESTED = "ingested"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"


class ReportStatus(StrEnum):
    PENDING = "pending"
    DRAFT = "draft"
    COMPLETE = "complete"
    STALE = "stale"


class NoteStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    DRAFT = "draft"
    COMPLETE = "complete"
    STALE = "stale"


class ImplementationStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    NOT_STARTED = "not_started"
    ATTACHED = "attached"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = None
    url: str | None = None


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    source_id: str
    kind: SourceKind
    location: Location
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Artifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: str
    note: str | None = None


class Workflow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion_status: IngestionStatus = IngestionStatus.PENDING
    report_status: ReportStatus = ReportStatus.PENDING
    note_status: NoteStatus = NoteStatus.NOT_REQUIRED
    implementation_status: ImplementationStatus = ImplementationStatus.NOT_APPLICABLE


class ResearchObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    object_id: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    rating: Rating | None = None
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    artifacts: Artifacts
    workflow: Workflow = Field(default_factory=Workflow)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class IntakeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    intake_id: str
    source: str
    kind: SourceKind
    status: IntakeStatus = IntakeStatus.PENDING
    object_id: str | None = None
    source_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EngineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    default_workspace: str | None = None


class CodexConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_profile: str | None = None
    evaluation_profile_file: str | None = None
    interests: list[str] = Field(default_factory=list)

    @field_validator("evaluation_profile_file")
    @classmethod
    def validate_evaluation_profile_file(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        profile_path = Path(value)
        if profile_path.is_absolute() or ".." in profile_path.parts:
            raise ValueError("evaluation_profile_file must be workspace-relative")
        return value


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    workspace_name: str = "pac-workspace"
    engine_min_version: str = "0.1.0"
    vault_dir: str = "vault"
    library_dir: str = "library"
    sources_dir: str = "sources"
    indexes_dir: str = "indexes"
    template_dir: str = "templates"
    codex: CodexConfig = Field(default_factory=CodexConfig)
