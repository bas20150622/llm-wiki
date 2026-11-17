import json

import pytest

from llm_wiki import cli
from llm_wiki.lint import lint

from conftest import write_page

SCHEMA_3_INDEX = """---
type: overview
title: "Wiki Index"
last_updated: 2026-01-01
---

# Wiki Index

Wiki: alpha | Total pages: 3 | Sources: 1 | Entities: 0 | Concepts: 2 | Comparisons: 0 | Howtos: 0 | Notes: 0

## Topics

| Topic | Description | Pages |
|-------|-------------|-------|
| tech | Technology | 2 |
| law | Law | 1 |

## Sources

| Page | Author | Topic | Date | Status |
|------|--------|-------|------|--------|
| [[s]] | x | tech | 2026-01-01 | active |

## Entities

| Page | Type | Topic | Sources |
|------|------|-------|---------|
| — | — | — | — |

## Concepts

| Page | Topic | Confidence | Sources |
|------|-------|------------|---------|
| [[a]] | tech | high | 1 |
| [[b]] | law | high | 1 |

## Reading list

Kept as is.
"""

SOURCE_FM = """
type: source
title: S
topic: tech
tags: []
last_updated: 2026-01-01
generated: {by: claude/test, at: 2026-01-01}
source: "[[raw/s.md]]"
"""

CONCEPT_FM = """
type: concept
title: {title}
topic: {topic}
tags: []
last_updated: 2026-01-01
generated: {{by: claude/test, at: 2026-01-01}}
sources: ["[[s]]"]
source_count: 1
"""


@pytest.fixture
def schema_3_wiki(make_wiki):
    root = make_wiki(topics={"tech": "Technology", "law": "Law"})
    for name, (old, new) in {"wiki.toml": ("schema_version = 4", "schema_version = 3"),
                             "CLAUDE.md": ("schema_version: 4", "schema_version: 3"),
                             "AGENTS.md": ("schema_version: 4", "schema_version: 3")}.items():
        path = root / name
        path.write_text(path.read_text().replace(old, new))
    for catalog in (root / "wiki").glob("index-*.md"):
        catalog.unlink()
    (root / "wiki" / "index.md").write_text(SCHEMA_3_INDEX)
    (root / "raw" / "s.md").write_text("raw source")
    write_page(root, "sources", "s", SOURCE_FM, "Links [[a]] and [[b]].\n\n## Raw Source\n[[raw/s.md]]")
    for slug, other, topic in (("a", "b", "tech"), ("b", "a", "law")):
        write_page(root, "concepts", slug, CONCEPT_FM.format(title=slug, topic=topic), f"See [[{other}]].\n\n## Sources\n- [[s]]")
    return root


def test_split_index_moves_rows_into_topic_catalogs(schema_3_wiki, capsys):
    root = schema_3_wiki
    assert any("split-index" in f.message for f in lint(root))

    cli.main(["split-index", str(root)])

    index = (root / "wiki" / "index.md").read_text()
    assert "| tech | Technology | 2 | [[index-tech]] |" in index and "| law | Law | 1 | [[index-law]] |" in index
    assert "## Sources" not in index and "## Concepts" not in index
    assert "## Reading list\n\nKept as is." in index
    tech = (root / "wiki" / "index-tech.md").read_text()
    assert "| Page | Author | Date | Status |\n|------|--------|------|--------|\n| [[s]] | x | 2026-01-01 | active |" in tech
    assert "| [[a]] | high | 1 |" in tech and "[[b]]" not in tech
    assert "| [[b]] | high | 1 |" in (root / "wiki" / "index-law.md").read_text()
    assert "schema_version = 4" in (root / "wiki.toml").read_text()
    assert "schema_version: 4" in (root / "CLAUDE.md").read_text() and "schema_version: 4" in (root / "AGENTS.md").read_text()
    log = [json.loads(line) for line in (root / "wiki" / "log.jsonl").read_text().splitlines()]
    assert log[-1]["op"] == "update" and log[-1]["created"] == ["index-tech", "index-law"]
    assert [f for f in lint(root) if f.severity != "info"] == []
    assert "2 catalogs" in capsys.readouterr().out


def test_split_index_refuses_rows_with_unregistered_topic_and_writes_nothing(schema_3_wiki, capsys):
    root = schema_3_wiki
    index = root / "wiki" / "index.md"
    index.write_text(index.read_text().replace("| [[b]] | law |", "| [[b]] | legal |"))
    before = index.read_text()

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["split-index", str(root)])

    assert exit_info.value.code == 2
    assert "[[b]] has topic 'legal'" in capsys.readouterr().err
    assert index.read_text() == before
    assert list((root / "wiki").glob("index-*.md")) == []
    assert "schema_version = 3" in (root / "wiki.toml").read_text()


def test_split_index_refuses_a_wiki_on_another_schema(make_wiki, capsys):
    root = make_wiki()
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["split-index", str(root)])
    assert exit_info.value.code == 2
    assert "schema_version 4" in capsys.readouterr().err


def test_split_index_refuses_other_wiki_inside_session(schema_3_wiki, monkeypatch):
    monkeypatch.setenv("LLM_WIKI_ACTIVE", "other")
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["split-index", str(schema_3_wiki)])
    assert exit_info.value.code == 2
