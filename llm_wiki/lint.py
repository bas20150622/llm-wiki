"""Deterministic wiki health checks.

These are the mechanical checks from the schema's Lint operation. Judgment checks (contradictions,
stale claims, missing concept pages) stay with the LLM, which runs this first and builds on the result.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

from llm_wiki.registry import read_identity, schema_warning

KIND_TYPE = {
    "sources": "source",
    "entities": "entity",
    "concepts": "concept",
    "comparisons": "comparison",
    "howtos": "howto",
    "notes": "note",
}
REQUIRED_FIELDS = ("type", "title", "topic", "tags", "last_updated")
CROSS_LINKED_KINDS = {"entities", "concepts", "comparisons", "howtos"}
NOTE_WORD_LIMIT = 250
SKIP_IN_WIKI = {".obsidian", "templates"}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
WIKILINK = re.compile(r"\[\[([^\]]*)\]\]")
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Finding:
    severity: str  # error | warning | info
    check: str
    page: str
    message: str


@dataclass
class Page:
    slug: str
    kind: str
    path: Path
    meta: dict
    body: str
    links: set[str] = field(default_factory=set)


def link_target(raw_link: str) -> str:
    return raw_link.split("|")[0].split("#")[0].strip()


def parse_markdown(path: Path) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, text
    return (meta if isinstance(meta, dict) else None), match.group(2)


def section_links(body: str, heading: str) -> list[str]:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    return [link_target(l) for l in WIKILINK.findall(match.group(1))] if match else []


def table_rows(markdown: str, heading: str) -> list[list[str]]:
    """Data rows of the first table under `## heading`, as lists of cell strings."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", markdown, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    rows = [line for line in match.group(1).splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows[2:]]


def frontmatter_links(value) -> list[str]:
    items = value if isinstance(value, list) else [value] if value else []
    return [link_target(m) for item in items for m in WIKILINK.findall(str(item))]


class Linter:
    def __init__(self, root: Path):
        self.root = root
        self.wiki = root / "wiki"
        self.findings: list[Finding] = []
        self.pages: dict[str, Page] = {}

    def add(self, severity: str, check: str, page: str, message: str) -> None:
        self.findings.append(Finding(severity, check, page, message))

    def run(self) -> list[Finding]:
        self.check_identity()
        self.load_pages()
        index_text = (self.wiki / "index.md").read_text(encoding="utf-8") if (self.wiki / "index.md").exists() else ""
        if not index_text:
            self.add("error", "index", "index", "wiki/index.md is missing")
        self.check_topics(index_text)
        self.check_links(index_text)
        self.check_cross_links()
        self.check_sources_fields()
        self.check_raw_targets()
        self.check_conversions()
        self.check_dates_and_generated()
        self.check_index(index_text)
        self.check_notes()
        self.check_stray_files()
        self.check_log()
        return sorted(self.findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.check, f.page))

    # --- loading ---------------------------------------------------------------

    def check_identity(self) -> None:
        identity = read_identity(self.root)
        warning = schema_warning(identity)
        if warning:
            self.add("warning", "identity", "wiki.toml", warning)
        claude_md = self.root / "CLAUDE.md"
        if not claude_md.exists() or f"wiki: {identity.get('name')}" not in claude_md.read_text(encoding="utf-8"):
            self.add("warning", "identity", "CLAUDE.md", f"CLAUDE.md does not declare `wiki: {identity.get('name')}`")

    def load_pages(self) -> None:
        for kind in KIND_TYPE:
            for path in sorted((self.wiki / kind).glob("*.md")):
                meta, body = parse_markdown(path)
                slug = path.stem
                if meta is None:
                    self.add("error", "frontmatter", slug, "missing or unparseable YAML frontmatter")
                    meta = {}
                links = {link_target(l) for l in WIKILINK.findall(path.read_text(encoding="utf-8"))}
                self.pages[slug] = Page(slug, kind, path, meta, body, links)
                missing = [f for f in REQUIRED_FIELDS if f not in meta]
                if meta and missing:
                    self.add("error", "frontmatter", slug, f"missing fields: {', '.join(missing)}")
                if meta.get("type") and meta["type"] != KIND_TYPE[kind]:
                    self.add("warning", "frontmatter", slug, f"type '{meta['type']}' does not match folder {kind}/")

    # --- checks ----------------------------------------------------------------

    def check_topics(self, index_text: str) -> None:
        if not re.search(r"^## Topics\s*$", index_text, re.MULTILINE):
            self.add("error", "topics", "index", "no `## Topics` registry in index.md")
            return
        # An empty registry is valid: topics are added as the wiki grows.
        registry = {
            row[0]: row[2] for row in table_rows(index_text, "Topics") if len(row) >= 3 and row[0] not in ("", "—")
        }
        counts: dict[str, int] = {}
        for page in self.pages.values():
            topic = page.meta.get("topic")
            counts[topic] = counts.get(topic, 0) + 1
            if topic not in registry:
                self.add("error", "topics", page.slug, f"topic '{topic}' is not in the registry")
        for topic, listed in registry.items():
            if listed.isdigit() and int(listed) != counts.get(topic, 0):
                self.add("warning", "topics", "index", f"topic '{topic}' lists {listed} pages, actual {counts.get(topic, 0)}")

    def resolve(self, target: str) -> bool:
        if target in self.pages or target in ("index", "overview"):
            return True
        return target.startswith("raw/") and (self.root / target).exists()

    def check_links(self, index_text: str) -> None:
        overview = self.wiki / "overview.md"
        sources = [(p.slug, p.links) for p in self.pages.values()]
        sources.append(("index", {link_target(l) for l in WIKILINK.findall(index_text)}))
        if overview.exists():
            sources.append(("overview", {link_target(l) for l in WIKILINK.findall(overview.read_text(encoding="utf-8"))}))
        for slug, links in sources:
            # Missing raw/ targets named in a source page's frontmatter are reported once, by check_raw_targets.
            page = self.pages.get(slug)
            reported = {t for f in ("source", "native_asset") for t in frontmatter_links(page.meta.get(f))} if page else set()
            for target in sorted(links - reported):
                if target.startswith(("/", "~")) or "../" in target:
                    self.add("error", "separation", slug, f"[[{target}]] points outside this wiki")
                elif not target:
                    self.add("error", "links", slug, "empty wikilink [[]]")
                elif not self.resolve(target):
                    self.add("error", "links", slug, f"broken wikilink [[{target}]]")

    def check_cross_links(self) -> None:
        inbound: dict[str, set[str]] = {slug: set() for slug in self.pages}
        for page in self.pages.values():
            for target in page.links:
                if target in inbound and target != page.slug:
                    inbound[target].add(page.slug)
        for page in self.pages.values():
            if page.kind != "notes" and not inbound[page.slug]:
                self.add("warning", "orphans", page.slug, "no inbound links from other pages")
            if page.kind not in CROSS_LINKED_KINDS:
                continue
            for target in sorted(page.links):
                other = self.pages.get(target)
                if other and other.kind in CROSS_LINKED_KINDS and page.slug not in other.links:
                    self.add("warning", "cross-links", page.slug, f"links [[{target}]], which does not link back")

    def check_sources_fields(self) -> None:
        for page in self.pages.values():
            if page.kind not in ("entities", "concepts"):
                continue
            listed = section_links(page.body, "Sources")
            cited = {t for t in page.links if t in self.pages and self.pages[t].kind == "sources"}
            count = page.meta.get("source_count")
            if count != len(listed):
                self.add("error", "provenance", page.slug, f"source_count is {count}, Sources section lists {len(listed)}")
            if set(listed) != cited:
                self.add("warning", "provenance", page.slug, f"cites {sorted(cited)} but Sources section lists {sorted(listed)}")
            if "sources" not in page.meta:
                self.add("warning", "provenance", page.slug, "missing `sources` frontmatter list")
            elif set(frontmatter_links(page.meta["sources"])) != set(listed):
                self.add("error", "provenance", page.slug, "`sources` frontmatter does not match the Sources section")

    def check_raw_targets(self) -> None:
        for page in self.pages.values():
            if page.kind != "sources":
                continue
            for field_name in ("source", "native_asset"):
                for target in frontmatter_links(page.meta.get(field_name)):
                    if not (self.root / target).exists():
                        self.add("error", "provenance", page.slug, f"{field_name} target {target} does not exist")

    def check_conversions(self) -> None:
        referenced = {}
        for page in self.pages.values():
            if page.kind == "sources":
                for target in frontmatter_links(page.meta.get("source")):
                    referenced[target] = page
        for md in sorted((self.root / "raw").rglob("*.md")):
            meta, _ = parse_markdown(md)
            if not meta or meta.get("type") != "converted-source":
                continue
            rel = md.relative_to(self.root).as_posix()
            native = md.with_name(str(meta.get("converted_from")))
            if not native.exists():
                self.add("error", "provenance", rel, f"native file {native.name} is missing")
            elif hashlib.sha256(native.read_bytes()).hexdigest() != meta.get("source_sha256"):
                self.add("warning", "provenance", rel, f"stale conversion: {native.name} changed since conversion")
            page = referenced.get(rel)
            if page and not page.meta.get("native_asset"):
                self.add("warning", "provenance", page.slug, f"converted source lacks native_asset (should link raw/{native.name})")

    def check_dates_and_generated(self) -> None:
        today = date.today()
        missing_generated = []
        for page in self.pages.values():
            stale = page.meta.get("stale_after")
            if isinstance(stale, date) and stale < today:
                self.add("warning", "stale", page.slug, f"stale_after {stale} has passed")
            if "generated" not in page.meta:
                missing_generated.append(page.slug)
        if missing_generated:
            self.add("info", "generated", "*", f"{len(missing_generated)} pages have no `generated` field (predate the schema)")

    def check_index(self, index_text: str) -> None:
        indexed = set()
        for heading in ("Sources", "Entities", "Concepts", "Comparisons", "Howtos", "Notes"):
            for row in table_rows(index_text, heading):
                indexed.update(link_target(l) for l in WIKILINK.findall(row[0]))
        for slug in sorted(set(self.pages) - indexed):
            self.add("error", "index", slug, "page is missing from index.md")
        for slug in sorted(indexed - set(self.pages)):
            self.add("error", "index", slug, "index.md lists a page that does not exist")
        total = re.search(r"Total pages:\s*(\d+)", index_text)
        if total and int(total.group(1)) != len(self.pages):
            self.add("warning", "index", "index", f"Total pages says {total.group(1)}, actual {len(self.pages)}")

    def check_notes(self) -> None:
        for page in self.pages.values():
            if page.kind != "notes":
                continue
            if not page.links:
                self.add("info", "notes", page.slug, "note has no links")
            words = len(page.body.split())
            if words > NOTE_WORD_LIMIT:
                self.add("info", "notes", page.slug, f"{words} words; may hold more than one idea")
            author = (page.meta.get("generated") or {}).get("by", "")
            if not str(author).startswith("human:"):
                self.add("info", "notes", page.slug, f"drafted by {author or 'unknown'}, not yet rewritten by the user")

    def check_stray_files(self) -> None:
        for path in sorted(self.wiki.rglob("*")):
            rel = path.relative_to(self.wiki)
            if not path.is_file() or rel.parts[0] in SKIP_IN_WIKI or path.name.startswith("."):
                continue
            if path.suffix not in (".md", ".jsonl"):
                self.add("warning", "stray-files", rel.as_posix(), "non-markdown file inside the vault")

    def check_log(self) -> None:
        log = self.wiki / "log.jsonl"
        if not log.exists():
            self.add("error", "log", "log.jsonl", "wiki/log.jsonl is missing")
            return
        for number, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                self.add("error", "log", f"log.jsonl:{number}", "line is not valid JSON")
                continue
            missing = [k for k in ("date", "op", "desc") if k not in entry]
            if missing:
                self.add("error", "log", f"log.jsonl:{number}", f"missing fields: {', '.join(missing)}")


def lint(root: Path) -> list[Finding]:
    return Linter(root).run()


def format_text(findings: list[Finding]) -> str:
    if not findings:
        return "No findings."
    lines = [f"{f.severity.upper():8} {f.check:12} {f.page}: {f.message}" for f in findings]
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_ORDER}
    lines.append(f"\n{counts['error']} errors, {counts['warning']} warnings, {counts['info']} info")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2)
