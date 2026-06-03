from __future__ import annotations

from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any

from pac.models import NoteStatus, ReportStatus, ResearchObject
from pac.paths import ProjectPaths
from pac.storage import Repository
from pac.utils import title_from_id


def build_dashboard(paths: ProjectPaths, *, output_format: str) -> dict[str, Any]:
    dashboard = dashboard_data(paths)
    if output_format == "json":
        return {"ok": True, "format": output_format, "dashboard": dashboard}
    if output_format == "obsidian":
        output_path = paths.root / paths.config.vault_dir / "Dashboard.md"
        content = render_obsidian_dashboard(dashboard)
    elif output_format == "html":
        output_path = paths.indexes_dir / "dashboard.html"
        content = render_html_dashboard(dashboard)
    else:
        raise ValueError(f"Unsupported dashboard format: {output_format}")

    created = not output_path.exists()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "format": output_format,
        "path": paths.relative(output_path),
        "created": created,
        "dashboard": dashboard,
    }


def dashboard_data(paths: ProjectPaths) -> dict[str, Any]:
    repo = Repository(paths)
    objects = repo.list_objects()
    object_lookup = {item.object_id: item for item in objects}
    rows = [_object_row(paths, item, object_lookup) for item in objects]
    tag_groups = _tag_groups(rows)
    connections = _connections(rows)
    ratings = Counter(str(item.rating) if item.rating else "unset" for item in objects)
    report_statuses = Counter(item.workflow.report_status.value for item in objects)
    note_statuses = Counter(item.workflow.note_status.value for item in objects)
    pending_reports = [
        row["object_id"]
        for row in rows
        if row["report_status"] in {ReportStatus.PENDING.value, ReportStatus.DRAFT.value}
        or not row["report_exists"]
    ]
    notes_needed = [
        row["object_id"]
        for row in rows
        if row["rating"] in {2, 3} and row["note_status"] != NoteStatus.COMPLETE.value
    ]
    return {
        "counts": {
            "objects": len(objects),
            "ratings": dict(ratings),
            "report_statuses": dict(report_statuses),
            "note_statuses": dict(note_statuses),
            "tags": len(tag_groups),
            "connections": len(connections),
        },
        "next_actions": {
            "pending_reports": pending_reports,
            "notes_needed": notes_needed,
        },
        "objects": rows,
        "tags": tag_groups,
        "connections": connections,
    }


def _object_row(
    paths: ProjectPaths,
    research_object: ResearchObject,
    object_lookup: dict[str, ResearchObject],
) -> dict[str, Any]:
    report_path = paths.root / research_object.artifacts.report
    note_path = (
        paths.root / research_object.artifacts.note
        if research_object.artifacts.note is not None
        else None
    )
    related_rows: list[dict[str, Any]] = []
    missing_related: list[str] = []
    for related_id in research_object.related:
        related = object_lookup.get(related_id)
        if related is None:
            missing_related.append(related_id)
            continue
        related_rows.append(
            {
                "object_id": related.object_id,
                "title": _title(related),
                "report_link": _artifact_wiki_link(paths, related, artifact_kind="report"),
                "note_link": _artifact_wiki_link(paths, related, artifact_kind="note"),
            }
        )
    return {
        "object_id": research_object.object_id,
        "title": _title(research_object),
        "rating": research_object.rating,
        "tags": research_object.tags,
        "related": related_rows,
        "missing_related": missing_related,
        "report": research_object.artifacts.report,
        "note": research_object.artifacts.note,
        "report_link": _artifact_wiki_link(paths, research_object, artifact_kind="report"),
        "note_link": _artifact_wiki_link(paths, research_object, artifact_kind="note"),
        "report_exists": report_path.exists(),
        "note_exists": note_path.exists() if note_path is not None else False,
        "report_status": research_object.workflow.report_status.value,
        "note_status": research_object.workflow.note_status.value,
        "implementation_status": research_object.workflow.implementation_status.value,
    }


def _tag_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        for tag in row["tags"]:
            grouped[tag].append(
                {
                    "object_id": row["object_id"],
                    "title": row["title"],
                    "report_link": row["report_link"],
                }
            )
    return [
        {"tag": tag, "count": len(objects), "objects": objects}
        for tag, objects in sorted(grouped.items())
    ]


def _connections(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    connections: list[dict[str, str]] = []
    for row in rows:
        for related in row["related"]:
            connections.append(
                {
                    "object_id": row["object_id"],
                    "title": row["title"],
                    "report_link": row["report_link"],
                    "related_object_id": related["object_id"],
                    "related_title": related["title"],
                    "related_report_link": related["report_link"],
                }
            )
    return connections


def render_obsidian_dashboard(dashboard: dict[str, Any]) -> str:
    lines = [
        "# PaC Dashboard",
        "",
        "## Overview",
        "",
        f"- Objects: {dashboard['counts']['objects']}",
        f"- Tag groups: {dashboard['counts']['tags']}",
        f"- Curated connections: {dashboard['counts']['connections']}",
        "",
        "## Review Queue",
        "",
        "### Pending Reports",
        "",
        *_object_link_lines(
            dashboard["objects"], dashboard["next_actions"]["pending_reports"]
        ),
        "",
        "### Notes Needed",
        "",
        *_object_link_lines(dashboard["objects"], dashboard["next_actions"]["notes_needed"]),
        "",
        "## Ratings",
        "",
        *_count_lines(dashboard["counts"]["ratings"]),
        "",
        "## Tags",
        "",
        *_tag_lines(dashboard["tags"]),
        "",
        "## Related Objects",
        "",
        *_connection_lines(dashboard["connections"]),
        "",
        "## Dataview",
        "",
        "### Reports",
        "",
        "```dataview",
        "TABLE rating, status, tags, related, note",
        'FROM "Reports"',
        "SORT rating DESC, file.name ASC",
        "```",
        "",
        "### Notes",
        "",
        "```dataview",
        "TABLE rating, status, tags, related, report",
        'FROM "Notes"',
        "SORT file.mtime DESC",
        "```",
        "",
    ]
    return "\n".join(lines)


def _object_link_lines(rows: list[dict[str, Any]], object_ids: list[str]) -> list[str]:
    by_id = {row["object_id"]: row for row in rows}
    if not object_ids:
        return ["- None"]
    return [
        f"- {by_id[object_id]['report_link']} (`{object_id}`)"
        for object_id in object_ids
        if object_id in by_id
    ]


def _count_lines(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- None"]
    return [f"- {key}: {value}" for key, value in sorted(counts.items())]


def _tag_lines(tags: list[dict[str, Any]]) -> list[str]:
    if not tags:
        return ["- None"]
    lines: list[str] = []
    for group in tags:
        lines.append(f"### #{group['tag']}")
        lines.append("")
        for item in group["objects"]:
            lines.append(f"- {item['report_link']} (`{item['object_id']}`)")
        lines.append("")
    return lines


def _connection_lines(connections: list[dict[str, str]]) -> list[str]:
    if not connections:
        return ["- None"]
    return [
        f"- {item['report_link']} -> {item['related_report_link']}"
        for item in connections
    ]


def render_html_dashboard(dashboard: dict[str, Any]) -> str:
    rows = "\n".join(_object_html(row) for row in dashboard["objects"])
    object_count = dashboard["counts"]["objects"]
    connection_count = dashboard["counts"]["connections"]
    pending_report_count = len(dashboard["next_actions"]["pending_reports"])
    needed_note_count = len(dashboard["next_actions"]["notes_needed"])
    tag_rows = "\n".join(
        f"<li><strong>{escape(group['tag'])}</strong> "
        f"<span>{group['count']} object(s)</span></li>"
        for group in dashboard["tags"]
    )
    connection_rows = "\n".join(
        f"<li>{escape(item['title'])} -> {escape(item['related_title'])}</li>"
        for item in dashboard["connections"]
    )
    if not tag_rows:
        tag_rows = "<li>None</li>"
    if not connection_rows:
        connection_rows = "<li>None</li>"
    return f"""\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PaC Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17201c;
      --muted: #66736d;
      --line: #d8ded9;
      --panel: #ffffff;
      --page: #f4f7f5;
      --accent: #0f766e;
      --warn: #b45309;
    }}
    body {{
      margin: 0;
      background: var(--page);
      color: var(--ink);
      font-family:
        Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }}
    h1, h2 {{
      margin: 0;
      line-height: 1.15;
    }}
    h1 {{
      font-size: 32px;
      font-weight: 700;
    }}
    h2 {{
      font-size: 18px;
      margin-bottom: 12px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric strong {{
      display: block;
      font-size: 28px;
      margin-bottom: 4px;
    }}
    .metric span, .muted {{
      color: var(--muted);
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
      gap: 16px;
      align-items: start;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      font-size: 14px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .tag {{
      border: 1px solid #9cc8c0;
      color: var(--accent);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      white-space: nowrap;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    li + li {{
      margin-top: 8px;
    }}
    @media (max-width: 780px) {{
      header, .grid {{
        display: block;
      }}
      section + section {{
        margin-top: 16px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>PaC Dashboard</h1>
        <p class="muted">Reports, notes, tags, and curated connections.</p>
      </div>
    </header>
    <div class="summary">
      <div class="metric"><strong>{object_count}</strong><span>Objects</span></div>
      <div class="metric">
        <strong>{pending_report_count}</strong><span>Pending reports</span>
      </div>
      <div class="metric">
        <strong>{needed_note_count}</strong><span>Notes needed</span>
      </div>
      <div class="metric">
        <strong>{connection_count}</strong><span>Connections</span>
      </div>
    </div>
    <div class="grid">
      <section>
        <h2>Objects</h2>
        <table>
          <thead>
            <tr><th>Title</th><th>Rating</th><th>Report</th><th>Note</th><th>Tags</th></tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
      </section>
      <div>
        <section>
          <h2>Tags</h2>
          <ul>{tag_rows}</ul>
        </section>
        <section style="margin-top: 16px;">
          <h2>Related Objects</h2>
          <ul>{connection_rows}</ul>
        </section>
      </div>
    </div>
  </main>
</body>
</html>
"""


def _object_html(row: dict[str, Any]) -> str:
    tags = "".join(f"<span class=\"tag\">{escape(tag)}</span>" for tag in row["tags"])
    if not tags:
        tags = "<span class=\"muted\">None</span>"
    rating = escape(str(row["rating"])) if row["rating"] else "unset"
    note = escape(row["note_status"])
    return (
        "<tr>"
        f"<td><strong>{escape(row['title'])}</strong><br><span class=\"muted\">"
        f"{escape(row['object_id'])}</span></td>"
        f"<td>{rating}</td>"
        f"<td>{escape(row['report_status'])}</td>"
        f"<td>{note}</td>"
        f"<td><div class=\"tags\">{tags}</div></td>"
        "</tr>"
    )


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
    target = _vault_wiki_target(paths, Path(artifact))
    return _wiki_link(target, _title(research_object))


def _vault_wiki_target(paths: ProjectPaths, artifact: Path) -> str:
    try:
        target = artifact.relative_to(paths.config.vault_dir)
    except ValueError:
        target = artifact
    return target.with_suffix("").as_posix()


def _wiki_link(target: str, title: str) -> str:
    alias = " ".join(title.replace("|", " ").split())
    return f"[[{target}|{alias}]]"


def _title(research_object: ResearchObject) -> str:
    return research_object.title or title_from_id(research_object.object_id)
