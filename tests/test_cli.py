from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml
from conftest import full_report, run_cli, run_cli_without_workspace

from pac.workspace import _workspace_pyproject


def test_core_commands_emit_json(pac_root: Path) -> None:
    for args in (
        ("doctor", "--json"),
        ("status", "--json"),
        ("intake", "scan", "--json"),
        ("intake", "list", "--json"),
        ("object", "list", "--json"),
        ("index", "rebuild", "--json"),
        ("search", "anything", "--json"),
    ):
        code, payload = run_cli(pac_root, *args)
        assert code == 0
        assert "ok" in payload


def test_workspace_init_creates_private_workspace_skeleton(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    code, payload = run_cli_without_workspace("workspace", "init", str(workspace), "--json")

    assert code == 0
    assert payload["ok"] is True
    assert (workspace / "pac-workspace.yaml").exists()
    assert (workspace / "vault/Inbox").is_dir()
    assert (workspace / "vault/Reports").is_dir()
    assert (workspace / "vault/Notes").is_dir()
    assert (workspace / "library/intake").is_dir()
    assert (workspace / "sources/pdfs/original").is_dir()
    assert not (workspace / "src/pac").exists()
    assert "sources/pdfs/" in (workspace / ".gitignore").read_text(encoding="utf-8")
    assert 'pac = { path =' in (workspace / "pyproject.toml").read_text(encoding="utf-8")


def test_workspace_init_nested_under_engine_uses_parent_editable_dependency() -> None:
    pyproject = _workspace_pyproject(Path.cwd() / "pac-workspace")

    assert 'pac = { path = "..", editable = true }' in pyproject


def test_workspace_discovery_uses_environment_and_nearest_marker(
    pac_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = pac_root / "vault/Inbox"

    monkeypatch.setenv("PAC_WORKSPACE", str(pac_root))
    code, payload = run_cli_without_workspace("workspace", "info", "--json")
    assert code == 0
    assert payload["workspace"] == str(pac_root)

    monkeypatch.delenv("PAC_WORKSPACE")
    monkeypatch.chdir(nested)
    code, payload = run_cli_without_workspace("workspace", "info", "--json")
    assert code == 0
    assert payload["workspace"] == str(pac_root)


def test_missing_engine_config_uses_built_in_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "missing/config.yaml"
    monkeypatch.setenv("PAC_CONFIG", str(config_path))

    code, payload = run_cli_without_workspace("config", "show", "--scope", "engine", "--json")

    assert code == 0
    assert payload["ok"] is True
    assert payload["exists"] is False
    assert payload["path"] == str(config_path)
    assert payload["config"]["default_workspace"] is None


def test_engine_config_path_show_set_and_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "pac/config.yaml"
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("PAC_CONFIG", str(config_path))

    code, path_payload = run_cli_without_workspace(
        "config", "path", "--scope", "engine", "--json"
    )
    assert code == 0
    assert path_payload["path"] == str(config_path)

    code, set_payload = run_cli_without_workspace(
        "config",
        "set",
        "--scope",
        "engine",
        "default_workspace",
        str(workspace),
        "--json",
    )
    assert code == 0
    assert set_payload["config"]["default_workspace"] == str(workspace)
    assert config_path.exists()

    code, show_payload = run_cli_without_workspace(
        "config", "show", "--scope", "engine", "--json"
    )
    assert code == 0
    assert show_payload["config"]["default_workspace"] == str(workspace)

    code, unset_payload = run_cli_without_workspace(
        "config", "unset", "--scope", "engine", "default_workspace", "--json"
    )
    assert code == 0
    assert unset_payload["config"]["default_workspace"] is None


def test_engine_default_workspace_is_last_resolution_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "pac/config.yaml"
    default_workspace = tmp_path / "default-workspace"
    nested_workspace = tmp_path / "nested-workspace"
    env_workspace = tmp_path / "env-workspace"
    explicit_workspace = tmp_path / "explicit-workspace"
    monkeypatch.setenv("PAC_CONFIG", str(config_path))
    for workspace in (default_workspace, nested_workspace, env_workspace, explicit_workspace):
        code, payload = run_cli_without_workspace("workspace", "init", str(workspace), "--json")
        assert code == 0
        assert payload["ok"] is True

    run_cli_without_workspace(
        "config",
        "set",
        "--scope",
        "engine",
        "default_workspace",
        str(default_workspace),
        "--json",
    )

    monkeypatch.chdir(tmp_path)
    code, fallback_payload = run_cli_without_workspace("workspace", "info", "--json")
    assert code == 0
    assert fallback_payload["workspace"] == str(default_workspace)

    monkeypatch.chdir(nested_workspace / "vault/Inbox")
    code, nearest_payload = run_cli_without_workspace("workspace", "info", "--json")
    assert code == 0
    assert nearest_payload["workspace"] == str(nested_workspace)

    monkeypatch.setenv("PAC_WORKSPACE", str(env_workspace))
    code, env_payload = run_cli_without_workspace("workspace", "info", "--json")
    assert code == 0
    assert env_payload["workspace"] == str(env_workspace)

    code, explicit_payload = run_cli_without_workspace(
        "--workspace", str(explicit_workspace), "workspace", "info", "--json"
    )
    assert code == 0
    assert explicit_payload["workspace"] == str(explicit_workspace)


def test_invalid_engine_config_reports_error_only_when_fallback_is_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pac_root = tmp_path / "workspace"
    code, payload = run_cli_without_workspace("workspace", "init", str(pac_root), "--json")
    assert code == 0
    assert payload["ok"] is True

    config_path = tmp_path / "pac/config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("default_workspace: [not, a, string]\n", encoding="utf-8")
    monkeypatch.setenv("PAC_CONFIG", str(config_path))

    code, local_payload = run_cli(pac_root, "workspace", "info", "--json")
    assert code == 0
    assert local_payload["workspace"] == str(pac_root)

    outside_workspace = tmp_path / "outside"
    outside_workspace.mkdir()
    monkeypatch.chdir(outside_workspace)
    code, fallback_payload = run_cli_without_workspace("workspace", "info", "--json")
    assert code == 1
    assert fallback_payload["ok"] is False
    assert "Invalid engine config" in fallback_payload["error"]


def test_workspace_config_dotted_updates_validate_and_reject_unknown_keys(
    pac_root: Path,
) -> None:
    code, payload = run_cli(
        pac_root,
        "config",
        "set",
        "--scope",
        "workspace",
        "codex.interests",
        '["AI infra", "efficient LLMs", "RL"]',
        "--json",
    )

    assert code == 0
    assert payload["config"]["codex"]["interests"] == ["AI infra", "efficient LLMs", "RL"]

    code, bad_payload = run_cli(
        pac_root,
        "config",
        "set",
        "--scope",
        "workspace",
        "codex.unknown",
        "value",
        "--json",
    )

    assert code == 1
    assert bad_payload["ok"] is False
    assert "Invalid workspace config" in bad_payload["error"]


def test_context_build_includes_workspace_codex_profile(pac_root: Path) -> None:
    profile = pac_root / "codex/profiles/ai-infra.md"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        "# AI Infra\n\nFocus on AI infrastructure and efficient LLM systems.\n",
        encoding="utf-8",
    )
    run_cli(
        pac_root,
        "config",
        "set",
        "--scope",
        "workspace",
        "codex.evaluation_profile",
        "ai-infra",
        "--json",
    )
    run_cli(
        pac_root,
        "config",
        "set",
        "--scope",
        "workspace",
        "codex.evaluation_profile_file",
        "codex/profiles/ai-infra.md",
        "--json",
    )

    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )
    code, context_payload = run_cli(
        pac_root,
        "context",
        "build",
        "--id",
        ingest_payload["object_id"],
        "--purpose",
        "report",
        "--json",
    )

    assert code == 0
    assert context_payload["codex"]["evaluation_profile"] == "ai-infra"
    assert context_payload["codex"]["evaluation_profile_file"] == "codex/profiles/ai-infra.md"
    assert "AI infrastructure" in context_payload["codex"]["evaluation_profile_text"]
    assert context_payload["codex"]["warnings"] == []


def test_missing_codex_profile_reports_warning_without_generating_report(
    pac_root: Path,
) -> None:
    run_cli(
        pac_root,
        "config",
        "set",
        "--scope",
        "workspace",
        "codex.evaluation_profile_file",
        "codex/profiles/missing.md",
        "--json",
    )
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )

    code, context_payload = run_cli(
        pac_root,
        "context",
        "build",
        "--id",
        ingest_payload["object_id"],
        "--purpose",
        "report",
        "--json",
    )
    report = (pac_root / context_payload["report_file"]).read_text(encoding="utf-8")

    assert code == 0
    assert context_payload["codex"]["evaluation_profile_text"] is None
    assert any("missing" in warning.lower() for warning in context_payload["codex"]["warnings"])
    assert "## Rating" not in report
    assert "Codex: generate this report" in report


def test_intake_add_handles_pdf_url_arxiv_and_github(pac_root: Path) -> None:
    pdf = pac_root / "sources/inbox/Interesting Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\nfake pdf")

    cases = [
        (str(pdf), "pdf"),
        ("https://arxiv.org/abs/2501.12345", "arxiv"),
        ("https://github.com/example/research-code", "github_repo"),
        ("https://example.com/post", "url"),
    ]
    for source, expected_kind in cases:
        code, payload = run_cli(pac_root, "intake", "add", "--source", source, "--json")
        assert code == 0
        assert payload["ok"] is True
        assert payload["intake"]["kind"] == expected_kind


def test_ingest_pdf_creates_metadata_and_stub_without_report_prose_or_rating(
    pac_root: Path,
) -> None:
    pdf = pac_root / "sources/inbox/Interesting Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\nfake pdf")

    _, add_payload = run_cli(pac_root, "intake", "add", "--source", str(pdf), "--json")
    intake_id = add_payload["intake"]["intake_id"]
    code, ingest_payload = run_cli(pac_root, "intake", "ingest", "--id", intake_id, "--json")

    assert code == 0
    assert ingest_payload["ok"] is True
    object_id = ingest_payload["object_id"]
    object_yaml = yaml.safe_load((pac_root / f"library/objects/{object_id}.yaml").read_text())
    report = (pac_root / f"vault/Reports/{object_id}.md").read_text(encoding="utf-8")

    assert object_yaml["rating"] is None
    assert object_yaml["workflow"]["report_status"] == "pending"
    assert "## Rating" not in report
    assert "One-Sentence Takeaway" not in report
    assert "Codex: generate this report" in report


def test_object_ids_are_stable_and_filename_safe(pac_root: Path) -> None:
    source = "https://arxiv.org/abs/2501.12345"
    _, first = run_cli(pac_root, "intake", "add", "--source", source, "--json")
    _, second = run_cli(pac_root, "intake", "add", "--source", source, "--json")
    code, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", first["intake"]["intake_id"], "--json"
    )

    assert code == 0
    assert first["intake"]["intake_id"] == second["intake"]["intake_id"]
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", ingest_payload["object_id"])


def test_report_validation_catches_stub_missing_required_sections(pac_root: Path) -> None:
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )

    code, payload = run_cli(
        pac_root, "report", "validate", "--id", ingest_payload["object_id"], "--json"
    )

    assert code == 0
    assert payload["ok"] is False
    assert any("Missing report section" in error for error in payload["errors"])


def test_note_creation_requires_important_rating_and_has_no_body_template(
    pac_root: Path,
) -> None:
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )
    object_id = ingest_payload["object_id"]

    _, early_note = run_cli(pac_root, "note", "ensure", "--id", object_id, "--json")
    assert early_note["ok"] is False

    run_cli(pac_root, "object", "update", "--id", object_id, "--rating", "2", "--json")
    code, payload = run_cli(pac_root, "note", "ensure", "--id", object_id, "--json")
    note = (pac_root / payload["note"]).read_text(encoding="utf-8")

    assert code == 0
    assert payload["ok"] is True
    assert "## " not in note
    assert "vault/Notes/AGENTS.md" in note


def test_object_update_replaces_tags_and_related_objects(pac_root: Path) -> None:
    _, first_add = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, first_ingest = run_cli(
        pac_root, "intake", "ingest", "--id", first_add["intake"]["intake_id"], "--json"
    )
    _, second_add = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.67890",
        "--json",
    )
    _, second_ingest = run_cli(
        pac_root, "intake", "ingest", "--id", second_add["intake"]["intake_id"], "--json"
    )

    code, payload = run_cli(
        pac_root,
        "object",
        "update",
        "--id",
        first_ingest["object_id"],
        "--tags",
        '["topic/attention", "pe/rope"]',
        "--related",
        f'["{second_ingest["object_id"]}"]',
        "--json",
    )

    assert code == 0
    assert payload["object"]["tags"] == ["topic/attention", "pe/rope"]
    assert payload["object"]["related"] == [second_ingest["object_id"]]

    object_yaml = yaml.safe_load(
        (pac_root / f"library/objects/{first_ingest['object_id']}.yaml").read_text()
    )
    assert object_yaml["tags"] == ["topic/attention", "pe/rope"]
    assert object_yaml["related"] == [second_ingest["object_id"]]


def test_object_update_rejects_invalid_tags_and_related_objects(pac_root: Path) -> None:
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )
    object_id = ingest_payload["object_id"]

    invalid_cases = (
        ("--tags", '["#attention"]', "Invalid tag"),
        ("--tags", '["attention"]', "Invalid tag"),
        ("--related", '["missing-object"]', "Unknown related object"),
        ("--related", f'["{object_id}"]', "cannot relate object to itself"),
    )
    for option, value, expected_error in invalid_cases:
        code, payload = run_cli(
            pac_root,
            "object",
            "update",
            "--id",
            object_id,
            option,
            value,
            "--json",
        )

        assert code == 1
        assert expected_error in payload["error"]


def test_frontmatter_sync_preserves_report_and_note_bodies(pac_root: Path) -> None:
    _, first_add = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, first_ingest = run_cli(
        pac_root, "intake", "ingest", "--id", first_add["intake"]["intake_id"], "--json"
    )
    _, second_add = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.67890",
        "--json",
    )
    _, second_ingest = run_cli(
        pac_root, "intake", "ingest", "--id", second_add["intake"]["intake_id"], "--json"
    )
    object_id = first_ingest["object_id"]
    related_id = second_ingest["object_id"]
    report_path = pac_root / f"vault/Reports/{object_id}.md"
    report_path.write_text(full_report(object_id), encoding="utf-8")

    run_cli(
        pac_root,
        "object",
        "update",
        "--id",
        object_id,
        "--rating",
        "2",
        "--tags",
        '["topic/attention"]',
        "--related",
        f'["{related_id}"]',
        "--json",
    )
    report_text = report_path.read_text(encoding="utf-8")
    report_frontmatter = frontmatter(report_text)

    assert report_frontmatter["type"] == "report"
    assert report_frontmatter["tags"] == ["topic/attention"]
    assert report_frontmatter["related"] == [related_id]
    assert "[[Reports/" in report_frontmatter["related_reports"][0]
    assert "## Core Idea" in report_text

    _, note_payload = run_cli(pac_root, "note", "ensure", "--id", object_id, "--json")
    note_path = pac_root / note_payload["note"]
    note_path.write_text(
        note_path.read_text(encoding="utf-8") + "\n# Deep Dive\n\nPreserved body.\n",
        encoding="utf-8",
    )

    run_cli(
        pac_root,
        "object",
        "update",
        "--id",
        object_id,
        "--tags",
        '["topic/attention", "method/rag"]',
        "--json",
    )
    note_text = note_path.read_text(encoding="utf-8")
    note_frontmatter = frontmatter(note_text)

    assert note_frontmatter["type"] == "note"
    assert note_frontmatter["report"].startswith("[[Reports/")
    assert note_frontmatter["tags"] == ["topic/attention", "method/rag"]
    assert "# Deep Dive\n\nPreserved body." in note_text


def test_dashboard_builds_json_obsidian_and_html_views(pac_root: Path) -> None:
    _, first_add = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, first_ingest = run_cli(
        pac_root, "intake", "ingest", "--id", first_add["intake"]["intake_id"], "--json"
    )
    _, second_add = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.67890",
        "--json",
    )
    _, second_ingest = run_cli(
        pac_root, "intake", "ingest", "--id", second_add["intake"]["intake_id"], "--json"
    )
    first_id = first_ingest["object_id"]
    second_id = second_ingest["object_id"]
    (pac_root / f"vault/Reports/{first_id}.md").write_text(
        full_report(first_id), encoding="utf-8"
    )
    run_cli(
        pac_root,
        "object",
        "update",
        "--id",
        first_id,
        "--rating",
        "2",
        "--tags",
        '["topic/attention", "pe/rope"]',
        "--related",
        f'["{second_id}"]',
        "--json",
    )

    code, json_payload = run_cli(
        pac_root, "dashboard", "build", "--format", "json", "--json"
    )
    assert code == 0
    assert json_payload["dashboard"]["counts"]["objects"] == 2
    assert json_payload["dashboard"]["counts"]["ratings"]["2"] == 1
    assert second_id in json_payload["dashboard"]["next_actions"]["pending_reports"]
    assert first_id in json_payload["dashboard"]["next_actions"]["notes_needed"]
    assert any(group["tag"] == "topic/attention" for group in json_payload["dashboard"]["tags"])

    code, obsidian_payload = run_cli(
        pac_root, "dashboard", "build", "--format", "obsidian", "--json"
    )
    dashboard_md = (pac_root / "vault/Dashboard.md").read_text(encoding="utf-8")
    assert code == 0
    assert obsidian_payload["path"] == "vault/Dashboard.md"
    assert "# PaC Dashboard" in dashboard_md
    assert "```dataview" in dashboard_md
    assert f"[[Reports/{first_id}|" in dashboard_md
    assert "#topic/attention" in dashboard_md

    code, html_payload = run_cli(
        pac_root, "dashboard", "build", "--format", "html", "--json"
    )
    dashboard_html = (pac_root / "indexes/dashboard.html").read_text(encoding="utf-8")
    assert code == 0
    assert html_payload["path"] == "indexes/dashboard.html"
    assert "<!doctype html>" in dashboard_html
    assert "topic/attention" in dashboard_html
    assert first_id in dashboard_html


def test_github_and_url_ingestion_register_without_clone_or_download(pac_root: Path) -> None:
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://github.com/example/research-code",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )

    source_yaml = yaml.safe_load(
        (pac_root / f"library/sources/{ingest_payload['source_id']}.yaml").read_text()
    )
    assert source_yaml["kind"] == "github_repo"
    assert source_yaml["location"]["url"] == "https://github.com/example/research-code"
    assert source_yaml["location"]["path"] is None
    assert source_yaml["metadata"]["clone_status"] == "not_cloned"


def test_annotation_import_never_overwrites_original_pdf(pac_root: Path) -> None:
    original = pac_root / "sources/inbox/Paper.pdf"
    original.write_bytes(b"%PDF-1.4\noriginal")
    annotated = pac_root / "sources/inbox/Paper annotated.pdf"
    annotated.write_bytes(b"%PDF-1.4\nannotated")

    _, add_payload = run_cli(pac_root, "intake", "add", "--source", str(original), "--json")
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )
    object_id = ingest_payload["object_id"]
    stored_original = pac_root / f"sources/pdfs/original/{object_id}.pdf"
    before = stored_original.read_bytes()

    code, payload = run_cli(
        pac_root, "annotation", "import", "--id", object_id, "--source", str(annotated), "--json"
    )

    assert code == 0
    assert payload["ok"] is True
    assert stored_original.read_bytes() == before
    assert (pac_root / payload["stored_path"]).read_bytes() == b"%PDF-1.4\nannotated"


def test_doctor_detects_missing_directory_invalid_yaml_and_missing_artifact(
    pac_root: Path,
) -> None:
    shutil.rmtree(pac_root / "vault/Reports")
    (pac_root / "library/objects/bad.yaml").write_text("not: [valid", encoding="utf-8")

    code, payload = run_cli(pac_root, "doctor", "--json")

    assert code == 0
    assert payload["ok"] is False
    messages = [issue["message"] for issue in payload["issues"]]
    assert any("Missing directory: vault/Reports" in message for message in messages)
    assert any("Invalid YAML" in message for message in messages)


def test_index_rebuild_produces_searchable_sqlite_index(pac_root: Path) -> None:
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.12345",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )
    object_id = ingest_payload["object_id"]
    (pac_root / f"vault/Reports/{object_id}.md").write_text(
        full_report(object_id), encoding="utf-8"
    )

    code, index_payload = run_cli(pac_root, "index", "rebuild", "--json")
    search_code, search_payload = run_cli(pac_root, "search", "contextual", "--json")

    assert code == 0
    assert index_payload["ok"] is True
    assert (pac_root / "indexes/pac.sqlite").exists()
    assert search_code == 0
    assert search_payload["ok"] is True
    assert any(result["object_id"] == object_id for result in search_payload["results"])


def test_context_prefers_workspace_template_and_falls_back_to_engine_default(
    pac_root: Path,
) -> None:
    _, add_payload = run_cli(
        pac_root,
        "intake",
        "add",
        "--source",
        "https://arxiv.org/abs/2501.67890",
        "--json",
    )
    _, ingest_payload = run_cli(
        pac_root, "intake", "ingest", "--id", add_payload["intake"]["intake_id"], "--json"
    )
    object_id = ingest_payload["object_id"]

    _, override_payload = run_cli(
        pac_root, "context", "build", "--id", object_id, "--purpose", "report", "--json"
    )
    assert override_payload["template_file"] == "templates/report.md"

    (pac_root / "templates/report.md").unlink()
    _, fallback_payload = run_cli(
        pac_root, "context", "build", "--id", object_id, "--purpose", "report", "--json"
    )
    assert fallback_payload["template_file"].endswith(
        "src/pac/assets/workspace_template/templates/report.md"
    )


def frontmatter(markdown: str) -> dict[str, object]:
    assert markdown.startswith("---\n")
    parts = markdown.split("---\n", 2)
    assert len(parts) == 3
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict)
    return data
