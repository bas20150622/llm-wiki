"""Create a new wiki instance, or (re)write the identity files of an existing one."""

import json
import shutil
from datetime import date
from pathlib import Path
from string import Template

from llm_wiki import SCHEMA_VERSION
from llm_wiki.registry import SCHEMA_DIR, WikiError, permission_path

TEMPLATES = Path(__file__).parent / "templates"
CONTENT_DIRS = ("sources", "entities", "concepts", "comparisons", "howtos", "notes", "templates")


def render(template: str, **values: str) -> str:
    return Template((TEMPLATES / f"{template}.tmpl").read_text(encoding="utf-8")).substitute(**values)


def write_identity(root: Path, name: str, scope: str, user_id: str) -> None:
    """Write wiki.toml, CLAUDE.md, AGENTS.md, and the local model setting. Overwrites existing files."""
    values = {
        "name": name,
        "scope": scope,
        "user_id": user_id,
        "schema_version": str(SCHEMA_VERSION),
        "schema_import": permission_path(SCHEMA_DIR / "CLAUDE.md"),
        "schema_agents": str(SCHEMA_DIR / "AGENTS.md"),
    }
    (root / "wiki.toml").write_text(render("wiki.toml", **values), encoding="utf-8")
    (root / "CLAUDE.md").write_text(render("CLAUDE.md", **values), encoding="utf-8")
    (root / "AGENTS.md").write_text(render("AGENTS.md", **values), encoding="utf-8")
    local_settings = root / ".claude" / "settings.local.json"
    if not local_settings.exists():
        local_settings.parent.mkdir(parents=True, exist_ok=True)
        local_settings.write_text(json.dumps({"model": "sonnet"}, indent=2) + "\n", encoding="utf-8")


# Page tables in each topic catalog (wiki/index-<topic>.md) and their default columns.
CATALOG_TABLES = {
    "Sources": ["Page", "Author", "Date", "Status"],
    "Entities": ["Page", "Type", "Sources"],
    "Concepts": ["Page", "Confidence", "Sources"],
    "Comparisons": ["Page", "Items"],
    "Howtos": ["Page", "Theme"],
    "Notes": ["Page", "Last updated"],
}
REGISTRY_HEADER = ["Topic", "Description", "Pages", "Index"]


def catalog_name(topic: str) -> str:
    return f"index-{topic}"


def markdown_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("-" * (len(h) + 2) for h in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows or [["—"] * len(header)]]
    return "\n".join(lines)


def registry_section(rows: list[tuple[str, str, str]]) -> str:
    """The `## Topics` registry from (topic, description, page count) rows."""
    table = markdown_table(REGISTRY_HEADER, [[t, d, n, f"[[{catalog_name(t)}]]"] for t, d, n in rows])
    if not rows:
        table = "\n".join(table.splitlines()[:2])  # An empty registry has no placeholder row.
    return f"## Topics\n\n{table}\n"


def index_page(name: str, topics: dict[str, str]) -> str:
    return f"""---
type: overview
title: "Wiki Index"
last_updated: {date.today().isoformat()}
---

# Wiki Index

Wiki: {name} | Total pages: 0 | Sources: 0 | Entities: 0 | Concepts: 0 | Comparisons: 0 | Howtos: 0 | Notes: 0

{registry_section([(t, d, "0") for t, d in topics.items()])}"""


def catalog_page(topic: str, tables: dict[str, tuple[list[str], list[list[str]]]] | None = None) -> str:
    """A topic catalog. `tables` maps each heading in CATALOG_TABLES to (header, rows); missing ones are empty."""
    tables = tables or {}
    sections = "\n".join(
        f"## {heading}\n\n{markdown_table(*tables.get(heading, (header, [])))}\n" for heading, header in CATALOG_TABLES.items()
    )
    return f"""---
type: overview
title: "Index: {topic}"
last_updated: {date.today().isoformat()}
---

# Index: {topic}

Pages with `topic: {topic}`. The topic registry and totals are in [[index]].

{sections}"""


def overview_page(topics: dict[str, str]) -> str:
    sections = "\n".join(f"## {t.replace('-', ' ').title()}\n\nNo content yet.\n" for t in topics)
    if not topics:
        sections = "No topics yet. A section is added here when a topic is registered.\n"
    return f"""---
type: overview
title: "Wiki Overview"
last_updated: {date.today().isoformat()}
---

# Wiki Overview

{sections}"""


def create_wiki(root: Path, name: str, scope: str, user_id: str, topics: dict[str, str]) -> None:
    if root.exists() and any(root.iterdir()):
        raise WikiError(f"{root} exists and is not empty.")

    wiki = root / "wiki"
    for sub in ("raw/assets", *(f"wiki/{d}" for d in CONTENT_DIRS)):
        (root / sub).mkdir(parents=True, exist_ok=True)
    write_identity(root, name, scope, user_id)

    (wiki / "index.md").write_text(index_page(name, topics), encoding="utf-8")
    for topic in topics:
        (wiki / f"{catalog_name(topic)}.md").write_text(catalog_page(topic), encoding="utf-8")
    (wiki / "overview.md").write_text(overview_page(topics), encoding="utf-8")
    topic_text = f"topics {', '.join(topics)}" if topics else "no topics yet"
    created = ["index", *(catalog_name(t) for t in topics), "overview"]
    entry = {"date": date.today().isoformat(), "op": "create", "desc": f"Created wiki '{name}' with {topic_text}", "created": created}
    (wiki / "log.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    (wiki / "templates" / "note.md").write_text(render("note.md", user_id=user_id), encoding="utf-8")
    shutil.copytree(TEMPLATES / "obsidian", root / ".obsidian")
