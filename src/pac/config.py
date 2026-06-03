from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from pac.models import EngineConfig, WorkspaceConfig

ENGINE_CONFIG_ENV = "PAC_CONFIG"
ENGINE_CONFIG_FILE = "config.yaml"


class ConfigError(ValueError):
    pass


def engine_config_path() -> Path:
    configured_path = os.environ.get(ENGINE_CONFIG_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    config_home = Path(xdg_config_home).expanduser() if xdg_config_home else Path.home() / ".config"
    return (config_home / "pac" / ENGINE_CONFIG_FILE).resolve()


def load_engine_config(path: Path | None = None) -> EngineConfig:
    config_path = path or engine_config_path()
    if not config_path.exists():
        return EngineConfig()
    data = load_yaml_mapping(config_path, label="engine config")
    return validate_engine_config(data, path=config_path)


def validate_engine_config(data: dict[str, Any], *, path: Path | None = None) -> EngineConfig:
    try:
        return EngineConfig.model_validate(data)
    except ValidationError as exc:
        source = f" {path}" if path else ""
        raise ConfigError(f"Invalid engine config{source}: {exc}") from exc


def validate_workspace_config(data: dict[str, Any], *, path: Path | None = None) -> WorkspaceConfig:
    try:
        return WorkspaceConfig.model_validate(data)
    except ValidationError as exc:
        source = f" {path}" if path else ""
        raise ConfigError(f"Invalid workspace config{source}: {exc}") from exc


def load_yaml_mapping(path: Path, *, label: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {label} {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{label.capitalize()} must be a mapping: {path}")
    return data


def parse_yaml_value(value: str) -> Any:
    try:
        return yaml.safe_load(value)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML value: {exc}") from exc


def set_dotted_value(data: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    updated = deepcopy(data)
    parent = _dotted_parent(updated, key, create=True)
    parent[_last_key(key)] = value
    return updated


def unset_dotted_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    updated = deepcopy(data)
    try:
        parent = _dotted_parent(updated, key, create=False)
    except ConfigError:
        return updated
    parent.pop(_last_key(key), None)
    return updated


def write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _dotted_parent(data: dict[str, Any], key: str, *, create: bool) -> dict[str, Any]:
    parts = _key_parts(key)
    current = data
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            if not create:
                raise ConfigError(f"Missing config key: {key}")
            child = {}
            current[part] = child
        if not isinstance(child, dict):
            raise ConfigError(f"Cannot update nested config key through scalar value: {part}")
        current = child
    return current


def _key_parts(key: str) -> list[str]:
    parts = key.split(".")
    if any(part == "" for part in parts):
        raise ConfigError(f"Invalid config key: {key}")
    return parts


def _last_key(key: str) -> str:
    return _key_parts(key)[-1]
