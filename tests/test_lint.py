import pytest

from llm_wiki.lint import lint

from conftest import write_page

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
topic: tech
tags: []
last_updated: 2026-01-01
generated: {{by: claude/test, at: 2026-01-01}}
sources: ["[[s]]"]
source_count: 1
"""


def index_with(root, rows, topic_count):
    index = root / "wiki" / "index.md"
    text = index.read_text()
    text = text.replace("| tech | Technology | 0 |", f"| tech | Technology | {topic_count} |")
    text = text.replace("Total pages: 0", f"Total pages: {topic_count}")
    for heading, row in rows:
        text = text.replace(f"## {heading}\n\n", f"## {heading}\n\n", 1)
        marker = f"## {heading}\n"
        head, _, tail = text.partition(marker)
        lines = tail.split("\n")
        # Insert after the header and separator rows of the table.
        lines.insert(3, row)
        text = head + marker + "\n".join(lines)
    index.write_text(text)


def build_clean_wiki(make_wiki):
    root = make_wiki()
    (root / "raw" / "s.md").write_text("raw source")
    write_page(root, "sources", "s", SOURCE_FM, "Links [[a]] and [[b]].\n\n## Raw Source\n[[raw/s.md]]")
    for slug, other in (("a", "b"), ("b", "a")):
        write_page(root, "concepts", slug, CONCEPT_FM.format(title=slug), f"See [[{other}]].\n\n## Sources\n- [[s]]")
    index_with(
        root,
        [("Sources", "| [[s]] | x | tech | 2026-01-01 | active |"),
         ("Concepts", "| [[a]] | tech | high | 1 |"),
         ("Concepts", "| [[b]] | tech | high | 1 |")],
        topic_count=3,
    )
    return root


def checks(findings, severity=None):
    return {(f.check, f.page) for f in findings if severity in (None, f.severity)}


def test_clean_wiki_has_no_errors_or_warnings(make_wiki):
    findings = lint(build_clean_wiki(make_wiki))
    assert [f for f in findings if f.severity != "info"] == []


def test_reports_broken_links_counts_topics_and_one_way_links(make_wiki):
    root = build_clean_wiki(make_wiki)
    write_page(root, "concepts", "c", CONCEPT_FM.format(title="c").replace("topic: tech", "topic: nope").replace("source_count: 1", "source_count: 2"),
               "Links [[a]] and [[missing]] and [[../escape]].\n\n## Sources\n- [[s]]")
    findings = lint(root)
    found = checks(findings)
    assert ("links", "c") in found
    assert ("separation", "c") in found
    assert ("topics", "c") in found
    assert ("provenance", "c") in found          # source_count 2 vs 1 listed
    assert ("cross-links", "c") in found         # c -> a, a does not link back
    assert ("index", "c") in found               # not in index
    assert ("orphans", "c") in found


def test_reports_missing_raw_target_once(make_wiki):
    root = build_clean_wiki(make_wiki)
    (root / "raw" / "s.md").unlink()
    findings = [f for f in lint(root) if f.page == "s"]
    assert [(f.check, f.severity) for f in findings] == [("provenance", "error")]


def test_missing_sources_frontmatter_is_a_warning(make_wiki):
    root = build_clean_wiki(make_wiki)
    path = root / "wiki" / "concepts" / "a.md"
    path.write_text(path.read_text().replace('sources: ["[[s]]"]\n', ""))
    assert ("provenance", "a") in checks(lint(root), "warning")


def test_notes_are_reported_not_required_to_cite(make_wiki):
    root = build_clean_wiki(make_wiki)
    write_page(root, "notes", "idea", "type: note\ntitle: Idea\ntopic: tech\ntags: []\nlast_updated: 2026-01-01\ngenerated: {by: claude/x, at: 2026-01-01}",
               "word " * 300)
    index_with(root, [("Notes", "| [[idea]] | tech | 2026-01-01 |")], topic_count=4)
    findings = lint(root)
    note_findings = {(f.check, f.severity) for f in findings if f.page == "idea"}
    assert note_findings == {("notes", "info")}
    messages = " ".join(f.message for f in findings if f.page == "idea")
    assert "no links" in messages and "300 words" in messages and "drafted by claude/x" in messages


def test_stale_conversion_and_stray_files(make_wiki):
    root = build_clean_wiki(make_wiki)
    (root / "raw" / "r.pdf").write_bytes(b"new bytes")
    (root / "raw" / "r.md").write_text('---\ntype: "converted-source"\nconverted_from: "r.pdf"\nsource_sha256: "old"\n---\n\nbody\n')
    (root / "wiki" / "concepts" / "export.pptx").write_bytes(b"x")
    found = checks(lint(root), "warning")
    assert ("provenance", "raw/r.md") in found
    assert ("stray-files", "concepts/export.pptx") in found


def test_missing_topics_section_is_an_error(make_wiki):
    root = make_wiki()
    index = root / "wiki" / "index.md"
    index.write_text(index.read_text().replace("## Topics", "## Something else"))
    assert ("topics", "index") in checks(lint(root), "error")


def test_page_needs_registered_topic_even_when_registry_is_empty(make_wiki):
    root = make_wiki(topics={})
    write_page(root, "notes", "idea", "type: note\ntitle: Idea\ntopic: tech\ntags: []\nlast_updated: 2026-01-01\ngenerated: {by: human:test, at: 2026-01-01}",
               "An idea. [[index]]")
    assert ("topics", "idea") in checks(lint(root), "error")


def test_bad_log_line(make_wiki):
    root = build_clean_wiki(make_wiki)
    with (root / "wiki" / "log.jsonl").open("a") as log:
        log.write("not json\n")
    assert ("log", "log.jsonl:2") in checks(lint(root), "error")


def test_malformed_frontmatter_values_are_findings_not_crashes(make_wiki):
    root = make_wiki()
    page_fm = "type: concept\ntitle: T\ntags: []\nlast_updated: 2026-01-01\nsource_count: 0\nsources: []\n"
    write_page(root, "concepts", "stale", page_fm + "topic: tech\nstale_after: 2020-01-01T10:00:00", "body")
    write_page(root, "concepts", "multi", page_fm + "topic: [tech, other]", "body")
    note_fm = "type: note\ntitle: N\ntopic: tech\ntags: []\nlast_updated: 2026-01-01\n"
    write_page(root, "notes", "plain", note_fm + "generated: human:test", "body")
    for number, value in enumerate(("sub/x.pdf", '""', "[a]")):
        (root / "raw" / f"bad{number}.md").write_text(f"---\ntype: converted-source\nconverted_from: {value}\n---\n\nbody\n")

    found = lint(root)

    assert ("stale", "stale") in checks(found, "warning")
    assert ("topics", "multi") in checks(found, "error")
    assert ("notes", "plain") in checks(found, "info")
    assert sum(1 for f in found if f.check == "provenance" and "converted_from must be a file name" in f.message) == 3


def test_non_utf8_files_are_findings_not_crashes(make_wiki):
    root = make_wiki()
    page_fm = "type: concept\ntitle: T\ntopic: tech\ntags: []\nlast_updated: 2026-01-01\nsource_count: 0\nsources: []\n"
    write_page(root, "concepts", "latin", page_fm, "body")
    bad = b"---\ntype: x\n---\n\ncaf\xe9\n"
    (root / "wiki" / "concepts" / "latin.md").write_bytes(bad)
    (root / "wiki" / "overview.md").write_bytes(bad)
    (root / "wiki" / "log.jsonl").write_bytes(b'{"date": "x", "op": "y", "desc": "caf\xe9"}\n')
    (root / "CLAUDE.md").write_bytes(b"wiki: alpha caf\xe9")
    (root / "raw" / "clip.md").write_bytes(bad)

    found = lint(root)

    encoding = {f.page for f in found if f.check == "encoding"}
    assert encoding == {"latin", "overview", "log.jsonl", "CLAUDE.md"}


def test_non_utf8_index_is_reported_once(make_wiki):
    root = make_wiki()
    (root / "wiki" / "index.md").write_bytes(b"caf\xe9")
    found = lint(root)
    assert ("encoding", "index") in checks(found, "error")
    assert not any("is missing" in f.message for f in found)


def test_stale_after_that_is_not_a_date_is_a_warning(make_wiki):
    root = make_wiki()
    page_fm = "type: concept\ntitle: T\ntopic: tech\ntags: []\nlast_updated: 2026-01-01\nsource_count: 0\nsources: []\n"
    write_page(root, "concepts", "quoted", page_fm + 'stale_after: "2020-01-01"', "body")
    write_page(root, "concepts", "empty", page_fm + "stale_after:", "body")
    write_page(root, "concepts", "past", page_fm + "stale_after: 2020-01-01", "body")

    stale = {f.page: f.message for f in lint(root) if f.check == "stale"}

    assert "not a YYYY-MM-DD date" in stale["quoted"]
    assert "empty" not in stale
    assert "has passed" in stale["past"]


def test_non_utf8_wiki_toml_is_a_refusal(make_wiki, capsys):
    from llm_wiki import cli

    root = make_wiki()
    (root / "wiki.toml").write_bytes(b'name = "caf\xe9"\n')
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["lint", str(root)])
    assert exit_info.value.code == 2
    assert "wiki.toml" in capsys.readouterr().err


def test_source_slug_joins_directories_to_the_stem():
    from pathlib import Path

    from llm_wiki.lint import source_slug

    assert source_slug(Path("book.md")) == "book"
    assert source_slug(Path("course/module-1.md")) == "course-module-1"
    assert source_slug(Path("a/b/c.md")) == "a-b-c"


def test_nested_raw_source_named_after_its_path_is_clean(make_wiki):
    root = build_clean_wiki(make_wiki)
    (root / "raw" / "course").mkdir()
    (root / "raw" / "course" / "intro.md").write_text("raw source")
    (root / "raw" / "assets" / "notes.md").write_text("not a source")
    write_page(root, "sources", "course-intro", SOURCE_FM.replace("raw/s.md", "raw/course/intro.md"),
               "Links [[a]].\n\n## Raw Source\n[[raw/course/intro.md]]")
    index_with(root, [("Sources", "| [[course-intro]] | x | tech | 2026-01-01 | active |")], topic_count=4)
    assert [f for f in lint(root) if f.check == "source-names"] == []


def test_raw_files_with_the_same_source_name_are_an_error(make_wiki):
    root = build_clean_wiki(make_wiki)
    (root / "raw" / "a").mkdir()
    (root / "raw" / "a" / "b-c.md").write_text("one")
    (root / "raw" / "a-b").mkdir()
    (root / "raw" / "a-b" / "c.md").write_text("two")
    assert ("source-names", "a-b-c") in checks(lint(root), "error")
    (root / "raw" / "a-b-c.md").write_text("three")
    clash = [f for f in lint(root) if f.check == "source-names"]
    assert len(clash) == 1 and clash[0].message.count("raw/") == 3


def test_source_page_not_named_after_its_raw_path_is_a_warning(make_wiki):
    root = build_clean_wiki(make_wiki)
    (root / "raw" / "course").mkdir()
    (root / "raw" / "course" / "s.md").write_text("raw source")
    page = root / "wiki" / "sources" / "s.md"
    page.write_text(page.read_text().replace("raw/s.md", "raw/course/s.md"))
    found = [f for f in lint(root) if f.check == "source-names"]
    assert [(f.severity, f.page) for f in found] == [("warning", "s")]
    assert "course-s.md" in found[0].message
