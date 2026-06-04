# LLM Wiki

A personal knowledge base maintained by LLMs, based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Instead of RAG (re-deriving knowledge every query), the LLM incrementally builds and maintains a persistent wiki of interlinked markdown files. Knowledge compounds over time — cross-references are already there, contradictions have been flagged, synthesis reflects everything you've read.

## How It Works

**Three layers:**

| Layer | Owner | Purpose |
|-------|-------|---------|
| `raw/` | You | Immutable source documents — articles, papers, notes, clippings |
| `wiki/` | LLM | Generated pages — summaries, entities, concepts, comparisons |
| Schema files | Both | CLAUDE.md / AGENTS.md / chatgpt-instructions.md govern LLM behavior |

**Three operations:**

- **Ingest** — drop a source in `raw/`, tell the LLM to process it. It writes a summary, creates/updates entity and concept pages, maintains cross-references, updates the index.
- **Query** — ask questions against the wiki. The LLM reads the index, finds relevant pages, synthesizes an answer. Good answers get filed back as new pages.
- **Lint** — health-check the wiki for contradictions, orphan pages, stale claims, missing cross-references.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+

## Installation

### Python environment (for document conversion)

```bash
cd llm-wiki
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python docling --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
```

This installs [Docling](https://github.com/DS4SD/docling) (IBM's ML-based document converter) with CPU-only PyTorch. Supports PDF, DOCX, PPTX, and XLSX.

To convert a file:
```bash
.venv/bin/python scripts/convert.py raw/my-report.pdf
```

This creates `raw/my-report.md` alongside the original. The LLM reads the markdown version.

### Obsidian (required)

1. Open Obsidian
2. "Open folder as vault" -> select the `llm-wiki/` directory
3. Install the **Dataview** plugin (Settings -> Community plugins -> Browse -> "Dataview")
4. Recommended: install **Obsidian Web Clipper** browser extension for capturing articles

### Claude Code

```bash
cd llm-wiki
claude
```

Claude Code reads `CLAUDE.md` automatically. No additional setup needed.

### OpenAI Codex CLI

```bash
cd llm-wiki
codex
```

Codex reads `AGENTS.md` automatically. No additional setup needed.

### ChatGPT (web UI)

1. Open `chatgpt-instructions.md`
2. Copy everything below the `---` line
3. Paste into one of:
   - **Custom Instructions** (Settings -> Personalization -> Custom Instructions)
   - **Custom GPT** system prompt (if creating a dedicated GPT)
   - **Start of conversation** (paste at the top of a new chat)

ChatGPT cannot write files directly — it outputs markdown blocks that you copy into the wiki.

## Quick Start

1. Save an article or note as a markdown file in `raw/` (Obsidian Web Clipper works well for this)
2. Tell the LLM: "Ingest raw/my-article.md"
3. The LLM reads it, discusses key points with you, then creates/updates wiki pages
4. Browse the results in Obsidian — check the graph view to see connections

## Domains

This wiki covers five domains:

- **Music Theory** — harmony, rhythm, composition, genres, artists
- **Technology** — software, AI/ML, tools, frameworks, research
- **Consulting** — frameworks, methodologies, industry analysis
- **Self-Improvement** — psychology, habits, health, productivity
- **Raw Notes** — anything that doesn't fit the above

## Tips

- **Obsidian Web Clipper** converts web articles to markdown — great for quickly adding sources
- **Download images locally**: in Obsidian Settings -> Files and links, attachment folder is already set to `raw/assets/`
- **Graph view** shows wiki structure — hubs, orphans, clusters
- **Dataview queries** work on all frontmatter (e.g., list all concepts sorted by source count)
- The wiki is a git repo — you get version history for free
