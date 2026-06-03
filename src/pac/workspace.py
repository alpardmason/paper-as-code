from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from pac import __version__
from pac.assets import default_workspace_template_path
from pac.models import WorkspaceConfig
from pac.paths import WORKSPACE_REQUIRED_DIRECTORIES, ProjectPaths
from pac.services import doctor, model_json


def init_workspace(path: str | Path) -> dict[str, Any]:
    workspace_root = Path(path).expanduser().resolve()
    template_root = default_workspace_template_path()
    created: list[str] = []

    workspace_root.mkdir(parents=True, exist_ok=True)
    for source in sorted(template_root.rglob("*")):
        relative = source.relative_to(template_root)
        destination = workspace_root / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            created.append(relative.as_posix())

    for directory in WORKSPACE_REQUIRED_DIRECTORIES:
        destination = workspace_root / directory
        if not destination.exists():
            destination.mkdir(parents=True, exist_ok=True)
            created.append(directory)

    gitignore = workspace_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(_workspace_gitignore(), encoding="utf-8")
        created.append(".gitignore")

    pyproject = workspace_root / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(_workspace_pyproject(workspace_root), encoding="utf-8")
        created.append("pyproject.toml")

    config = ProjectPaths.from_workspace(workspace_root).config
    return {
        "ok": True,
        "workspace": str(workspace_root),
        "created": created,
        "config": model_json(config),
        "next_actions": [
            "Open vault/ in Obsidian.",
            "Run `uv sync` in the workspace.",
            "Run `uv run pac workspace doctor --json`.",
        ],
    }


def workspace_info(paths: ProjectPaths) -> dict[str, Any]:
    return {
        "ok": True,
        "workspace": str(paths.root),
        "config": model_json(paths.config),
        "engine_version": __version__,
        "directories": {
            "vault": paths.config.vault_dir,
            "library": paths.config.library_dir,
            "sources": paths.config.sources_dir,
            "indexes": paths.config.indexes_dir,
            "templates": paths.config.template_dir,
        },
    }


def workspace_doctor(paths: ProjectPaths) -> dict[str, Any]:
    return doctor(paths)


def _workspace_gitignore() -> str:
    return """\
.env
.DS_Store
.venv/
indexes/
sources/inbox/
sources/pdfs/
sources/repos/
sources/web/
*.sqlite
__pycache__/
.ruff_cache/
.mypy_cache/
.pytest_cache/
"""


def _workspace_pyproject(workspace_root: Path) -> str:
    engine_root = Path(__file__).resolve().parents[2]
    engine_path = Path(os.path.relpath(engine_root, start=workspace_root))

    dependency_path = _toml_string(engine_path.as_posix())
    return f"""\
[project]
name = "pac-workspace"
version = "0.1.0"
description = "Private PaC research workspace."
requires-python = ">=3.12"
dependencies = ["pac"]

[tool.uv.sources]
pac = {{ path = {dependency_path}, editable = true }}
"""


def default_workspace_config() -> WorkspaceConfig:
    return WorkspaceConfig()


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
