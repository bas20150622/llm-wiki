"""Convert non-markdown files in raw/ to markdown using Docling (CPU-only).

The output carries provenance frontmatter (source name, SHA-256, timestamp, tool version)
and page/slide/sheet markers so claims can be traced back to a location in the original.
"""

import hashlib
import importlib.metadata
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED = {".pdf", ".docx", ".pptx", ".xlsx"}
MARKER_LABEL = {".pdf": "page", ".pptx": "slide", ".xlsx": "sheet"}
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

EXIT_ERROR = 1
EXIT_REFUSED = 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_frontmatter(path: Path) -> dict | None:
    """Return the frontmatter of an existing markdown file, or None if absent/unparseable."""
    import yaml

    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def existing_output_action(output_path: Path, source_name: str, source_hash: str, force: bool) -> str:
    """Decide what to do when the output file exists: 'convert', 'skip', or exit with a refusal."""
    if not output_path.exists() or force:
        return "convert"

    meta = read_frontmatter(output_path)
    if not meta or meta.get("converted_from") != source_name:
        owner = meta.get("converted_from") if meta else None
        reason = (
            f"it was converted from '{owner}'"
            if owner
            else "it has no conversion frontmatter (hand-written or not made by this script)"
        )
        print(f"Refused: {output_path} exists and {reason}. Use --force to overwrite.")
        sys.exit(EXIT_REFUSED)

    if meta.get("source_sha256") == source_hash:
        return "skip"

    print(
        f"Refused: {source_name} has changed since {output_path} was converted "
        f"(converted_at {meta.get('converted_at')}). The existing file may contain edits. "
        "Use --force to reconvert."
    )
    sys.exit(EXIT_REFUSED)


def sheet_names_by_page(doc) -> dict[int, str]:
    """Map page number -> sheet name for XLSX documents."""
    from docling_core.types.doc import GroupItem, GroupLabel

    names = {}
    for group in doc.groups:
        if not isinstance(group, GroupItem) or group.label != GroupLabel.SHEET:
            continue
        for item, _ in doc.iterate_items(root=group):
            prov = getattr(item, "prov", None)
            if prov:
                names[prov[0].page_no] = group.name
                break
    return names


def body_with_markers(doc, suffix: str) -> str:
    """Export markdown, prefixed per page/slide/sheet with an HTML-comment marker."""
    label = MARKER_LABEL.get(suffix)
    page_numbers = sorted(doc.pages)
    if label is None or not page_numbers:
        return doc.export_to_markdown()

    sheets = sheet_names_by_page(doc) if suffix == ".xlsx" else {}
    parts = []
    for page_no in page_numbers:
        title = f": {sheets[page_no].replace('--', '- -')}" if page_no in sheets else ""
        parts.append(f"<!-- {label} {page_no}{title} -->\n\n{doc.export_to_markdown(page_no=page_no)}")
    return "\n\n".join(parts)


def frontmatter_block(source_name: str, source_hash: str) -> str:
    fields = {
        "type": "converted-source",
        "converted_from": source_name,
        "source_sha256": source_hash,
        "converted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "converted_by": f"docling/{importlib.metadata.version('docling')}",
    }
    # json.dumps output is valid YAML and keeps every value a string.
    lines = [f"{key}: {json.dumps(value)}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def convert(input_path: str, force: bool = False) -> str:
    path = Path(input_path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        print(f"Unsupported format: {path.suffix}")
        sys.exit(EXIT_ERROR)
    if not path.is_file():
        print(f"File not found: {path}")
        sys.exit(EXIT_ERROR)

    output_path = path.with_suffix(".md")
    source_hash = sha256(path)

    if existing_output_action(output_path, path.name, source_hash, force) == "skip":
        print(f"Up to date: {output_path} (matches {path.name})")
        return str(output_path)

    # Set before importing Docling so it never tries a GPU.
    os.environ["DOCLING_DEVICE"] = "cpu"
    os.environ["TORCH_DEVICE"] = "cpu"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    from docling.document_converter import DocumentConverter

    result = DocumentConverter().convert(str(path))
    content = frontmatter_block(path.name, source_hash) + body_with_markers(result.document, suffix) + "\n"

    tmp_path = output_path.with_name(output_path.name + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, output_path)
    print(f"Converted: {path} -> {output_path}")
    return str(output_path)
