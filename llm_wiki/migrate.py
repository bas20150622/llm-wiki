"""One-time migrations of an existing wiki to a newer schema version."""

import json
import re
from datetime import date
from pathlib import Path

from llm_wiki.lint import WIKILINK, read_text, table
from llm_wiki.registry import NAME_PATTERN, WikiError, read_identity
from llm_wiki.scaffold import CATALOG_TABLES, catalog_name, catalog_page, registry_section


def split_index(root: Path) -> list[str]:
    """Schema 3 -> 4: move the page tables of wiki/index.md into one catalog per topic.

    Everything is checked before anything is written, so a refusal leaves the wiki untouched.
    Page files are not changed. Returns the names of the catalogs created.
    """
    identity = read_identity(root)
    if identity.get("schema_version") != 3:
        raise WikiError(f"split-index migrates schema 3 wikis; {root} declares schema_version {identity.get('schema_version')}.")
    wiki = root / "wiki"
    index_path = wiki / "index.md"
    text = read_text(index_path) if index_path.exists() else None
    if text is None:
        raise WikiError(f"{index_path} is missing or not valid UTF-8.")

    header, rows = table(text, "Topics")
    if not header:
        raise WikiError("index.md has no `## Topics` registry.")
    registry = [(row + ["", ""])[:3] for row in rows if row and row[0] not in ("", "—")]
    topics = [topic for topic, _, _ in registry]
    invalid = [t for t in topics if not NAME_PATTERN.match(t)]
    if invalid:
        raise WikiError(f"Not split: topic names must be lowercase and hyphenated: {', '.join(invalid)}.")
    existing = [f"wiki/{catalog_name(t)}.md" for t in topics if (wiki / f"{catalog_name(t)}.md").exists()]
    if existing:
        raise WikiError(f"Not split: {', '.join(existing)} already exist.")

    tables: dict[str, dict[str, tuple[list[str], list[list[str]]]]] = {t: {} for t in topics}
    unknown = []
    for heading in CATALOG_TABLES:
        head, body = table(text, heading)
        if not head:
            continue
        try:
            column = [cell.lower() for cell in head].index("topic")
        except ValueError:
            raise WikiError(f"Not split: the `## {heading}` table has no Topic column.") from None
        by_topic: dict[str, list[list[str]]] = {t: [] for t in topics}
        for row in body:
            if not WIKILINK.search(row[0]):
                continue  # The "—" placeholder row of an empty table.
            topic = row[column] if column < len(row) else ""
            if topic not in by_topic:
                unknown.append(f"  {heading}: {row[0]} has topic '{topic}'")
                continue
            by_topic[topic].append(row[:column] + row[column + 1 :])
        for topic in topics:
            tables[topic][heading] = (head[:column] + head[column + 1 :], by_topic[topic])
    if unknown:
        raise WikiError("Not split: these rows have a topic that is not in the registry. Fix them first:\n" + "\n".join(unknown))

    for topic in topics:
        (wiki / f"{catalog_name(topic)}.md").write_text(catalog_page(topic, tables[topic]), encoding="utf-8")
    index_path.write_text(rewrite_index(text, registry), encoding="utf-8")
    set_schema_version(root, 3, 4)
    created = [catalog_name(t) for t in topics]
    entry = {"date": date.today().isoformat(), "op": "update", "desc": "Split index.md into per-topic catalogs (schema 4)",
             "created": created, "updated": ["index"]}
    with (wiki / "log.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")
    return created


def rewrite_index(text: str, registry: list[list[str]]) -> str:
    """index.md with the registry rebuilt and the page tables removed. Other sections are kept."""
    head, *sections = re.split(r"(?m)^(?=## )", text)
    kept = []
    for section in sections:
        heading = section.splitlines()[0][3:].strip()
        if heading == "Topics":
            kept.append(registry_section([(t, d, n) for t, d, n in registry]) + "\n")
        elif heading not in CATALOG_TABLES:
            kept.append(section)
    return (head + "".join(kept)).rstrip() + "\n"


def set_schema_version(root: Path, old: int, new: int) -> None:
    replacements = {
        "wiki.toml": (rf"(?m)^schema_version = {old}$", f"schema_version = {new}"),
        "CLAUDE.md": (rf"(?m)^schema_version: {old}$", f"schema_version: {new}"),
        "AGENTS.md": (rf"(?m)^schema_version: {old}$", f"schema_version: {new}"),
    }
    for name, (pattern, replacement) in replacements.items():
        path = root / name
        if path.exists():
            path.write_text(re.sub(pattern, replacement, path.read_text(encoding="utf-8")), encoding="utf-8")
