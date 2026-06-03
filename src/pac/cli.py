from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pac.config import (
    engine_config_path,
    load_engine_config,
    load_yaml_mapping,
    parse_yaml_value,
    set_dotted_value,
    unset_dotted_value,
    validate_engine_config,
    validate_workspace_config,
    write_model,
)
from pac.dashboard import build_dashboard
from pac.indexer import rebuild_index, search
from pac.models import Rating
from pac.paths import WORKSPACE_MARKER, ProjectPaths, WorkspaceNotFoundError
from pac.services import (
    PacError,
    add_intake,
    attach_implementation,
    build_context,
    doctor,
    ensure_note,
    ensure_report,
    import_annotation,
    ingest_intake,
    list_intakes,
    list_objects,
    model_json,
    scan_intake,
    show_object,
    status,
    update_object,
    validate_report,
)
from pac.storage import StorageError
from pac.workspace import init_workspace, workspace_doctor, workspace_info

Handler = Callable[[argparse.Namespace], dict[str, Any]]


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    try:
        result = args.handler(args)
    except (PacError, StorageError, ValueError, WorkspaceNotFoundError) as exc:
        _emit({"ok": False, "error": str(exc)}, json_output=getattr(args, "json", False))
        return 1
    _emit(result, json_output=getattr(args, "json", False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pac")
    parser.add_argument(
        "--workspace",
        default=None,
        help="PaC workspace root. Defaults to PAC_WORKSPACE or nearest pac-workspace.yaml.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Deprecated alias for --workspace.",
    )
    subparsers = parser.add_subparsers(dest="command")

    _command(subparsers, "doctor", _doctor)
    _command(subparsers, "status", _status)

    config = subparsers.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command")
    config_path = _command(config_sub, "path", _config_path)
    _add_config_scope(config_path)
    config_show = _command(config_sub, "show", _config_show)
    _add_config_scope(config_show)
    config_set = _command(config_sub, "set", _config_set)
    _add_config_scope(config_set)
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_unset = _command(config_sub, "unset", _config_unset)
    _add_config_scope(config_unset)
    config_unset.add_argument("key")

    workspace = subparsers.add_parser("workspace")
    workspace_sub = workspace.add_subparsers(dest="workspace_command")
    workspace_init = _command(workspace_sub, "init", _workspace_init)
    workspace_init.add_argument("path")
    _command(workspace_sub, "doctor", _workspace_doctor)
    _command(workspace_sub, "info", _workspace_info)

    intake = subparsers.add_parser("intake")
    intake_sub = intake.add_subparsers(dest="intake_command")
    intake_add = _command(intake_sub, "add", _intake_add)
    intake_add.add_argument("--source", required=True)
    intake_add.add_argument(
        "--kind",
        default="auto",
        choices=["auto", "pdf", "arxiv", "url", "github_repo", "web_snapshot"],
    )
    _command(intake_sub, "scan", _intake_scan)
    _command(intake_sub, "list", _intake_list)
    intake_ingest = _command(intake_sub, "ingest", _intake_ingest)
    intake_ingest.add_argument("--id", required=True)

    object_parser = subparsers.add_parser("object")
    object_sub = object_parser.add_subparsers(dest="object_command")
    _command(object_sub, "list", _object_list)
    object_show = _command(object_sub, "show", _object_show)
    object_show.add_argument("--id", required=True)
    object_update = _command(object_sub, "update", _object_update)
    object_update.add_argument("--id", required=True)
    object_update.add_argument("--rating", type=int, choices=[1, 2, 3])
    object_update.add_argument(
        "--tags",
        default=None,
        help='Replace tags with a YAML list, e.g. \'["topic/attention", "pe/rope"]\'.',
    )
    object_update.add_argument(
        "--related",
        default=None,
        help='Replace related object IDs with a YAML list, e.g. \'["2025-paper"]\'.',
    )

    report = subparsers.add_parser("report")
    report_sub = report.add_subparsers(dest="report_command")
    report_ensure = _command(report_sub, "ensure", _report_ensure)
    report_ensure.add_argument("--id", required=True)
    report_validate = _command(report_sub, "validate", _report_validate)
    report_validate.add_argument("--id", required=True)

    note = subparsers.add_parser("note")
    note_sub = note.add_subparsers(dest="note_command")
    note_ensure = _command(note_sub, "ensure", _note_ensure)
    note_ensure.add_argument("--id", required=True)

    context = subparsers.add_parser("context")
    context_sub = context.add_subparsers(dest="context_command")
    context_build = _command(context_sub, "build", _context_build)
    context_build.add_argument("--id", required=True)
    context_build.add_argument(
        "--purpose",
        required=True,
        choices=["report", "note", "implementation"],
    )

    annotation = subparsers.add_parser("annotation")
    annotation_sub = annotation.add_subparsers(dest="annotation_command")
    annotation_import = _command(annotation_sub, "import", _annotation_import)
    annotation_import.add_argument("--id", required=True)
    annotation_import.add_argument("--source", required=True)

    implementation = subparsers.add_parser("implementation")
    implementation_sub = implementation.add_subparsers(dest="implementation_command")
    implementation_attach = _command(implementation_sub, "attach", _implementation_attach)
    implementation_attach.add_argument("--id", required=True)
    implementation_attach.add_argument("--repo-path", required=True)

    index = subparsers.add_parser("index")
    index_sub = index.add_subparsers(dest="index_command")
    _command(index_sub, "rebuild", _index_rebuild)

    dashboard = subparsers.add_parser("dashboard")
    dashboard_sub = dashboard.add_subparsers(dest="dashboard_command")
    dashboard_build = _command(dashboard_sub, "build", _dashboard_build)
    dashboard_build.add_argument(
        "--format",
        default="obsidian",
        choices=["obsidian", "html", "json"],
        help="Dashboard output format.",
    )

    search_parser = _command(subparsers, "search", _search)
    search_parser.add_argument("query")

    return parser


def _command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    handler: Handler,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name)
    parser.add_argument("--json", action="store_true", help="Emit compact JSON output.")
    parser.set_defaults(handler=handler)
    return parser


def _add_config_scope(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope",
        default="engine",
        choices=["engine", "workspace"],
        help="Configuration scope.",
    )


def _paths(args: argparse.Namespace) -> ProjectPaths:
    return ProjectPaths.from_workspace(args.workspace or args.root)


def _config_path(args: argparse.Namespace) -> dict[str, Any]:
    path = _config_file_path(args)
    return {"ok": True, "scope": args.scope, "path": str(path), "exists": path.exists()}


def _config_show(args: argparse.Namespace) -> dict[str, Any]:
    if args.scope == "engine":
        path = engine_config_path()
        config = load_engine_config(path)
        return {
            "ok": True,
            "scope": args.scope,
            "path": str(path),
            "exists": path.exists(),
            "config": model_json(config),
        }

    paths = _paths(args)
    path = paths.root / WORKSPACE_MARKER
    return {
        "ok": True,
        "scope": args.scope,
        "path": str(path),
        "exists": path.exists(),
        "config": model_json(paths.config),
    }


def _config_set(args: argparse.Namespace) -> dict[str, Any]:
    value = parse_yaml_value(args.value)
    path = _config_file_path(args)
    data = _config_file_data(args.scope, path)
    updated = set_dotted_value(data, args.key, value)
    config = _validate_config_data(args.scope, updated, path)
    write_model(path, config)
    return {
        "ok": True,
        "scope": args.scope,
        "path": str(path),
        "config": model_json(config),
    }


def _config_unset(args: argparse.Namespace) -> dict[str, Any]:
    path = _config_file_path(args)
    data = _config_file_data(args.scope, path)
    updated = unset_dotted_value(data, args.key)
    config = _validate_config_data(args.scope, updated, path)
    write_model(path, config)
    return {
        "ok": True,
        "scope": args.scope,
        "path": str(path),
        "config": model_json(config),
    }


def _config_file_path(args: argparse.Namespace) -> Path:
    if args.scope == "engine":
        return engine_config_path()
    return _paths(args).root / WORKSPACE_MARKER


def _config_file_data(scope: str, path: Path) -> dict[str, Any]:
    if scope == "engine" and not path.exists():
        return {}
    return load_yaml_mapping(path, label=f"{scope} config")


def _validate_config_data(scope: str, data: dict[str, Any], path: Path) -> BaseModel:
    if scope == "engine":
        return validate_engine_config(data, path=path)
    return validate_workspace_config(data, path=path)


def _workspace_init(args: argparse.Namespace) -> dict[str, Any]:
    return init_workspace(args.path)


def _workspace_doctor(args: argparse.Namespace) -> dict[str, Any]:
    return workspace_doctor(_paths(args))


def _workspace_info(args: argparse.Namespace) -> dict[str, Any]:
    return workspace_info(_paths(args))


def _doctor(args: argparse.Namespace) -> dict[str, Any]:
    return doctor(_paths(args))


def _status(args: argparse.Namespace) -> dict[str, Any]:
    return status(_paths(args))


def _intake_add(args: argparse.Namespace) -> dict[str, Any]:
    return add_intake(_paths(args), source=args.source, kind=args.kind)


def _intake_scan(args: argparse.Namespace) -> dict[str, Any]:
    return scan_intake(_paths(args))


def _intake_list(args: argparse.Namespace) -> dict[str, Any]:
    return list_intakes(_paths(args))


def _intake_ingest(args: argparse.Namespace) -> dict[str, Any]:
    return ingest_intake(_paths(args), intake_id=args.id)


def _object_list(args: argparse.Namespace) -> dict[str, Any]:
    return list_objects(_paths(args))


def _object_show(args: argparse.Namespace) -> dict[str, Any]:
    return show_object(_paths(args), object_id=args.id)


def _object_update(args: argparse.Namespace) -> dict[str, Any]:
    rating: Rating | None = args.rating
    return update_object(
        _paths(args),
        object_id=args.id,
        rating=rating,
        tags=_optional_string_list(args.tags, label="tags"),
        related=_optional_string_list(args.related, label="related"),
    )


def _report_ensure(args: argparse.Namespace) -> dict[str, Any]:
    return ensure_report(_paths(args), object_id=args.id)


def _report_validate(args: argparse.Namespace) -> dict[str, Any]:
    return validate_report(_paths(args), object_id=args.id)


def _note_ensure(args: argparse.Namespace) -> dict[str, Any]:
    return ensure_note(_paths(args), object_id=args.id)


def _context_build(args: argparse.Namespace) -> dict[str, Any]:
    return build_context(_paths(args), object_id=args.id, purpose=args.purpose)


def _annotation_import(args: argparse.Namespace) -> dict[str, Any]:
    return import_annotation(_paths(args), object_id=args.id, source=args.source)


def _implementation_attach(args: argparse.Namespace) -> dict[str, Any]:
    return attach_implementation(_paths(args), object_id=args.id, repo_path=args.repo_path)


def _index_rebuild(args: argparse.Namespace) -> dict[str, Any]:
    return rebuild_index(_paths(args))


def _dashboard_build(args: argparse.Namespace) -> dict[str, Any]:
    return build_dashboard(_paths(args), output_format=args.format)


def _search(args: argparse.Namespace) -> dict[str, Any]:
    return search(_paths(args), args.query)


def _optional_string_list(value: str | None, *, label: str) -> list[str] | None:
    if value is None:
        return None
    parsed = parse_yaml_value(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError(f"{label} must be a YAML list of strings")
    return parsed


def _emit(result: dict[str, Any], *, json_output: bool) -> None:
    indent = None if json_output else 2
    print(json.dumps(result, indent=indent, sort_keys=False))
