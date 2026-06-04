"""Convert non-markdown files in raw/ to markdown using Docling (CPU-only)."""

import sys
import os

os.environ["DOCLING_DEVICE"] = "cpu"
os.environ["TORCH_DEVICE"] = "cpu"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from pathlib import Path
from docling.document_converter import DocumentConverter

SUPPORTED = {".pdf", ".docx", ".pptx", ".xlsx"}


def convert(input_path: str) -> str:
    path = Path(input_path)
    if path.suffix.lower() not in SUPPORTED:
        print(f"Unsupported format: {path.suffix}")
        sys.exit(1)

    output_path = path.with_suffix(".md")

    converter = DocumentConverter()
    result = converter.convert(str(path))
    markdown = result.document.export_to_markdown()

    output_path.write_text(markdown, encoding="utf-8")
    print(f"Converted: {path} -> {output_path}")
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/convert.py <path-to-file>")
        sys.exit(1)
    convert(sys.argv[1])
