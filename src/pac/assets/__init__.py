from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path


def default_workspace_template_path() -> Path:
    template = files("pac.assets").joinpath("workspace_template")
    with as_file(template) as path:
        return path
