# LLM Wiki Schema

You are maintaining a personal knowledge wiki. You write and maintain all wiki pages. The user curates sources and directs analysis. This file governs your behavior — read it fully before any operation.

## Architecture

```
raw/                     # Source documents — NEVER modify these
  assets/                # Images referenced by sources
wiki/                    # LLM-generated pages — you own this entirely
  sources/               # One summary per raw document
  entities/              # People, orgs, tools, albums, books
  concepts/              # Ideas, theories, frameworks
  comparisons/           # Side-by-side analyses
    howtos/                # Practical step-by-step guides
  index.md               # Content catalog — read this FIRST on every operation
  log.jsonl                 # Append-only chronological record
  overview.md            # High-level synthesis across all domains
scripts/
  convert.py             # Docling-based file converter (PDF, DOCX, PPTX, XLSX -> markdown)
.venv/                   # Python virtual environment (uv-managed)
```

## Document Conversion

Non-markdown files in `raw/` (PDF, DOCX, PPTX, XLSX) must be converted to markdown before ingestion. Use the Docling converter:

```bash
.venv/bin/python scripts/convert.py raw/filename.pdf
```

This creates `raw/filename.md` alongside the original. The original binary is preserved; the LLM reads the `.md` version.

Supported formats: `.pdf`, `.docx`, `.pptx`, `.xlsx`

## Domains

- `music-theory` — harmony, rhythm, composition, genres, artists, albums, instruments
- `technology` — software, AI/ML, tools, frameworks, architecture, research papers
- `consulting` — frameworks, methodologies, client management, industry analysis
- `self-improvement` — psychology, habits, health, productivity, goals
- `raw-notes` — anything that doesn't fit the above

## Naming Conventions

- Filenames: lowercase, hyphens, no spaces (e.g., `modal-interchange.md`)
- Source summaries match raw filenames: `raw/karpathy-llm-wiki.md` -> `wiki/sources/karpathy-llm-wiki.md`
- Use `[[wikilinks]]` everywhere, never markdown links for internal pages

## Frontmatter Schema

Every wiki page has YAML frontmatter. Common fields:

```yaml
---
type: source | entity | concept | comparison | howto | overview
title: Human-readable title
domain: music-theory | technology | consulting | self-improvement | raw-notes
tags: [lowercase-hyphenated-tags]
last_updated: YYYY-MM-DD
---
```

### Type-specific fields

**Source** (`wiki/sources/`):
```yaml
source: "[[raw/filename.md]]"
author: Author Name
date: YYYY-MM-DD
status: active | outdated
```

**Entity** (`wiki/entities/`):
```yaml
entity_type: person | organization | tool | album | book | framework
source_count: 0
```

**Concept** (`wiki/concepts/`):
```yaml
confidence: high | medium | low
source_count: 0
```

**Comparison** (`wiki/comparisons/`):
```yaml
items: [item-a, item-b]
```

**Howto** (`wiki/howtos/`):
```yaml
theme: cli-tools | mac | git | obsidian  # Cluster tag — reuse existing, add as needed
```

## Page Templates

### Source Summary

```markdown
## Key Claims
- Claim 1 — with context
- Claim 2 — with context

## Summary
2-3 paragraph summary of the source.

## Extracted Entities
- [[entity-name]] — brief role in this source

## Extracted Concepts
- [[concept-name]] — how it appears in this source

## Questions Raised
- Open question that this source raises but doesn't answer

## Raw Source
[[raw/filename.md]]
```

### Entity Page

```markdown
One-paragraph description of who/what this entity is.

## Key Facts
- Fact 1 ([[source-name|source]])
- Fact 2 ([[source-name|source]])

## Connections
- [[related-entity]] — relationship description
- [[related-concept]] — how they relate

## Sources
- [[source-1]]
- [[source-2]]
```

### Concept Page

```markdown
**Definition:** One-sentence definition.

## Explanation
2-3 paragraph explanation of the concept. Use concrete examples.

## Related Concepts
- [[related-concept]] — relationship description

## Sources
- [[source-1]]
- [[source-2]]

## Open Questions
- Unresolved question about this concept
```

### Comparison Page

```markdown
## Context
Why this comparison matters. 1-2 sentences.

## Comparison

| Dimension | Item A | Item B |
|-----------|--------|--------|
| Dimension 1 | ... | ... |
| Dimension 2 | ... | ... |

## Analysis
Key takeaways from the comparison.

## Verdict
When to choose each option.

## Sources
- [[source-1]]
- [[source-2]]
```

### Howto Page

```markdown
Brief description of what this guide covers and when you'd need it.

## Steps

1. First step
   ```bash
   command example
   ```
2. Second step
3. Third step

## Notes

- Gotchas, alternatives, or edge cases

## Related

- [[related-howto]] — related guide
- [[related-concept]] — underlying concept
```

## Operations

### Ingest

When the user adds a new source to `raw/` and asks you to process it:

1. If the source is a non-markdown file (PDF, DOCX, PPTX, XLSX), convert it first:
   ```bash
   .venv/bin/python scripts/convert.py raw/filename.ext
   ```
   Then proceed with the generated `.md` file.
2. Read the source document fully
3. Discuss key takeaways with the user
4. Create a source summary page in `wiki/sources/`
5. Identify entities — create or update entity pages, maintain `source_count`
6. Identify concepts — create or update concept pages, adjust `confidence` and `source_count`
7. Add cross-references in both directions between related pages
8. Update `wiki/index.md` with new entries
9. Update `wiki/overview.md` if the source meaningfully changes the big picture
10. Append to `wiki/log.jsonl`

### Query

When the user asks a question:

1. Read `wiki/index.md` to identify relevant pages
2. Read the relevant wiki pages
3. Synthesize an answer with `[[wikilinks]]` to sources
4. If the answer is substantial and reusable, offer to file it as a new wiki page
5. If filed, update `wiki/index.md` and append to `wiki/log.jsonl`

### Delete

When the user wants to remove a source from the wiki:

1. Confirm with the user which source to delete
2. Read the source summary in `wiki/sources/` to identify all linked entity and concept pages
3. For each linked entity page: remove citations, decrement `source_count`, delete the page if `source_count` reaches 0
4. For each linked concept page: remove citations, decrement `source_count`, delete if `source_count` reaches 0, adjust `confidence` if warranted
5. Delete the source summary from `wiki/sources/`
6. Delete the raw source file from `raw/` (and its converted `.md` if applicable)
7. Remove deleted pages from `wiki/index.md` and update counts
8. Update `wiki/overview.md` if the deletion meaningfully changes the big picture
9. Append a `delete` operation to `wiki/log.jsonl`

### Lint

When the user asks for a health check:

1. Read `wiki/index.md` and scan all wiki pages
2. Check for: contradictions, stale claims, orphan pages, missing concept pages, missing cross-references, outdated `source_count`, broken `[[wikilinks]]`
3. Report findings and fix with user approval

## Rules

1. **Never modify files in `raw/`.** The only exception is the Delete operation, which removes them entirely.
2. **Always use `[[wikilinks]]`** for internal references.
3. **Always update `wiki/index.md`** when creating or deleting pages.
4. **Always append to `wiki/log.jsonl`** after any operation.
5. **Cite sources.** Every factual claim must link to at least one source.
6. **Check `wiki/index.md` for existing pages** before creating new ones.
7. **Reuse existing tags** — check before inventing new ones.
8. **Keep `source_count` accurate.**
9. **Use defined domains only.** Don't invent new ones.
10. **Filenames: lowercase, hyphens.** No spaces, underscores, or capitals.
11. **One entity/concept per page.**
12. **Cross-reference aggressively.** Link related pages in both directions.

## Index Format

`wiki/index.md` uses markdown tables with sections for Sources, Entities, Concepts, Comparisons, Howtos. Each row has a wikilink plus key metadata. A summary line at the top shows total counts.

## Log Format

`wiki/log.jsonl` is append-only. Format: `## [YYYY-MM-DD] operation | description` followed by affected pages as wikilinks. Operations: `ingest`, `query`, `lint`, `delete`, `update`, `create`.
