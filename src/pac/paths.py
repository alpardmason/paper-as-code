from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pac.config import (
    ConfigError,
    load_engine_config,
    load_yaml_mapping,
    validate_workspace_config,
)
from pac.models import WorkspaceConfig

WORKSPACE_MARKER = "pac-workspace.yaml"

WORKSPACE_REQUIRED_DIRECTORIES = (
    "vault",
    "vault/Inbox",
    "vault/Reports",
    "vault/Notes",
    "sources",
    "sources/inbox",
    "sources/pdfs/original",
    "sources/pdfs/annotated",
    "sources/repos",
    "sources/web",
    "library",
    "library/intake",
    "library/objects",
    "library/sources",
    "templates",
    "indexes",
)

WORKSPACE_REQUIRED_AGENT_FILES = (
    "AGENTS.md",
    "vault/AGENTS.md",
    "vault/Inbox/AGENTS.md",
    "vault/Reports/AGENTS.md",
    "vault/Notes/AGENTS.md",
    "sources/AGENTS.md",
    "library/AGENTS.md",
    "templates/AGENTS.md",
)

# Backward-compatible aliases for tests or integrations that imported these names in v0.1.
REQUIRED_DIRECTORIES = WORKSPACE_REQUIRED_DIRECTORIES
REQUIRED_AGENT_FILES = WORKSPACE_REQUIRED_AGENT_FILES


class WorkspaceNotFoundError(RuntimeError):
    pass


class WorkspaceConfigError(WorkspaceNotFoundError):
    pass


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    config: WorkspaceConfig

    @classmethod
    def from_root(cls, root: str | Path | None = None) -> ProjectPaths:
        """Deprecated compatibility alias for workspace discovery."""
        return cls.from_workspace(root)

    @classmethod
    def from_workspace(cls, workspace: str | Path | None = None) -> ProjectPaths:
        if workspace is not None:
            root = Path(workspace).expanduser().resolve()
            return cls(root, _load_workspace_config(root))

        env_workspace = os.environ.get("PAC_WORKSPACE")
        if env_workspace:
            root = Path(env_workspace).expanduser().resolve()
            return cls(root, _load_workspace_config(root))

        try:
            return cls.discover(Path.cwd())
        except WorkspaceConfigError:
            raise
        except WorkspaceNotFoundError as exc:
            engine_config = load_engine_config()
            if engine_config.default_workspace:
                root = Path(engine_config.default_workspace).expanduser().resolve()
                return cls(root, _load_workspace_config(root))
            raise WorkspaceNotFoundError(
                "No PaC workspace found. Run `pac workspace init <path> --json`, "
                "pass `--workspace <path>`, set PAC_WORKSPACE, or configure "
                "`default_workspace` in the engine config."
            ) from exc

    @classmethod
    def discover(cls, start: Path) -> ProjectPaths:
        current = start.expanduser().resolve()
        for candidate in (current, *current.parents):
            if (candidate / WORKSPACE_MARKER).is_file():
                return cls(candidate, _load_workspace_config(candidate))
        raise WorkspaceNotFoundError(
            "No PaC workspace found. Run `pac workspace init <path> --json` "
            "or pass `--workspace <path>`."
        )

    def rel(self, relative: str) -> Path:
        return self.root / relative

    @property
    def intake_dir(self) -> Path:
        return self.root / self.config.library_dir / "intake"

    @property
    def objects_dir(self) -> Path:
        return self.root / self.config.library_dir / "objects"

    @property
    def sources_dir(self) -> Path:
        return self.root / self.config.library_dir / "sources"

    @property
    def original_pdfs_dir(self) -> Path:
        return self.root / self.config.sources_dir / "pdfs" / "original"

    @property
    def annotated_pdfs_dir(self) -> Path:
        return self.root / self.config.sources_dir / "pdfs" / "annotated"

    @property
    def report_dir(self) -> Path:
        return self.root / self.config.vault_dir / "Reports"

    @property
    def notes_dir(self) -> Path:
        return self.root / self.config.vault_dir / "Notes"

    @property
    def indexes_dir(self) -> Path:
        return self.root / self.config.indexes_dir

    @property
    def report_template(self) -> Path:
        workspace_template = self.root / self.config.template_dir / "report.md"
        if workspace_template.exists():
            return workspace_template

        from pac.assets import default_workspace_template_path

        return default_workspace_template_path() / "templates" / "report.md"

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path.expanduser())


def _load_workspace_config(root: Path) -> WorkspaceConfig:
    marker = root / WORKSPACE_MARKER
    if not marker.is_file():
        raise WorkspaceNotFoundError(f"Missing PaC workspace marker: {marker}")
    try:
        data = load_yaml_mapping(marker, label="workspace config")
        return validate_workspace_config(data, path=marker)
    except ConfigError as exc:
        raise WorkspaceConfigError(f"Invalid workspace config {marker}: {exc}") from exc
