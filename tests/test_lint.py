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
