from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from pac.models import IntakeRecord, ResearchObject, SourceRecord
from pac.paths import ProjectPaths


class StorageError(RuntimeError):
    pass


def load_yaml(path: Path) -> dict[str, object]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise StorageError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise StorageError(f"YAML document must be a mapping: {path}")
    return data


def save_yaml(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_model[ModelT: BaseModel](path: Path, model_cls: type[ModelT]) -> ModelT:
    try:
        return model_cls.model_validate(load_yaml(path))
    except ValidationError as exc:
        raise StorageError(f"Invalid metadata in {path}: {exc}") from exc


class Repository:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def intake_path(self, intake_id: str) -> Path:
        return self.paths.intake_dir / f"{intake_id}.yaml"

    def object_path(self, object_id: str) -> Path:
        return self.paths.objects_dir / f"{object_id}.yaml"

    def source_path(self, source_id: str) -> Path:
        return self.paths.sources_dir / f"{source_id}.yaml"

    def load_intake(self, intake_id: str) -> IntakeRecord:
        return load_model(self.intake_path(intake_id), IntakeRecord)

    def save_intake(self, record: IntakeRecord) -> None:
        save_yaml(self.intake_path(record.intake_id), record)

    def load_object(self, object_id: str) -> ResearchObject:
        return load_model(self.object_path(object_id), ResearchObject)

    def save_object(self, record: ResearchObject) -> None:
        save_yaml(self.object_path(record.object_id), record)

    def load_source(self, source_id: str) -> SourceRecord:
        return load_model(self.source_path(source_id), SourceRecord)

    def save_source(self, record: SourceRecord) -> None:
        save_yaml(self.source_path(record.source_id), record)

    def list_intakes(self) -> list[IntakeRecord]:
        return [
            load_model(path, IntakeRecord)
            for path in sorted(self.paths.intake_dir.glob("*.yaml"))
        ]

    def list_objects(self) -> list[ResearchObject]:
        return [
            load_model(path, ResearchObject)
            for path in sorted(self.paths.objects_dir.glob("*.yaml"))
        ]

    def list_sources(self) -> list[SourceRecord]:
        return [
            load_model(path, SourceRecord)
            for path in sorted(self.paths.sources_dir.glob("*.yaml"))
        ]
