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


def index_page(name: str, topics: dict[str, str]) -> str:
    topic_rows = "\n".join(f"| {t} | {d} | 0 |" for t, d in topics.items())
    empty = lambda cols: "| " + " | ".join(["—"] * cols) + " |"
    return f"""---
type: overview
title: "Wiki Index"
last_updated: {date.today().isoformat()}
---

# Wiki Index

Wiki: {name} | Total pages: 0 | Sources: 0 | Entities: 0 | Concepts: 0 | Comparisons: 0 | Howtos: 0 | Notes: 0

## Topics

| Topic | Description | Pages |
|-------|-------------|-------|
{topic_rows}

## Sources

| Page | Author | Topic | Date | Status |
|------|--------|-------|------|--------|
{empty(5)}

## Entities

| Page | Type | Topic | Sources |
|------|------|-------|---------|
{empty(4)}

## Concepts

| Page | Topic | Confidence | Sources |
|------|-------|------------|---------|
{empty(4)}

## Comparisons

| Page | Topic | Items |
|------|-------|-------|
{empty(3)}

## Howtos

| Page | Theme | Topic |
|------|-------|-------|
{empty(3)}

## Notes

| Page | Topic | Last updated |
|------|-------|--------------|
{empty(3)}
"""


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
    (wiki / "overview.md").write_text(overview_page(topics), encoding="utf-8")
    topic_text = f"topics {', '.join(topics)}" if topics else "no topics yet"
    entry = {"date": date.today().isoformat(), "op": "create", "desc": f"Created wiki '{name}' with {topic_text}", "created": ["index", "overview"]}
    (wiki / "log.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    (wiki / "templates" / "note.md").write_text(render("note.md", user_id=user_id), encoding="utf-8")
    shutil.copytree(TEMPLATES / "obsidian", wiki / ".obsidian")
