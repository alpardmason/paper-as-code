from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pac.cli import main  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_pac_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PAC_WORKSPACE", raising=False)
    monkeypatch.delenv("PAC_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))


@pytest.fixture
def pac_root(tmp_path: Path) -> Path:
    code, payload = run_cli_without_workspace("workspace", "init", str(tmp_path), "--json")
    assert code == 0
    assert payload["ok"] is True
    return tmp_path


def run_cli(root: Path, *args: str) -> tuple[int, dict[str, Any]]:
    output = StringIO()
    with redirect_stdout(output):
        code = main(("--workspace", str(root), *args))
    return code, json.loads(output.getvalue())


def run_cli_without_workspace(*args: str) -> tuple[int, dict[str, Any]]:
    output = StringIO()
    with redirect_stdout(output):
        code = main(args)
    return code, json.loads(output.getvalue())


def full_report(object_id: str, title: str = "Example Paper") -> str:
    sections = [
        "## Rating\n\n⭐⭐",
        "## One-Sentence Takeaway\n\nA useful contribution.",
        "## Why This Matters\n\nIt improves contextual retrieval workflows.",
        "## Core Idea\n\nThe method organizes evidence for later use.",
        "## Technical Details\n\nThe implementation details are concrete.",
        "## Evidence and Results\n\nThe results are promising.",
        "## Limitations and Risks\n\nThe evidence is incomplete.",
        "## Implementation Relevance\n\nThis can guide engineering experiments.",
        "## Related Work and Connections\n\nRelated to retrieval systems.",
        "## Recommended Next Actions\n\nCreate a deep note.",
    ]
    return (
        "---\n"
        f"object_id: {object_id}\n"
        f"title: {title}\n"
        "rating: 2\n"
        "status: complete\n"
        "---\n\n"
        f"# {title}\n\n"
        + "\n\n".join(sections)
        + "\n"
    )
