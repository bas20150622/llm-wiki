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

This creates `raw/filename.md` alongside the original. The original binary is preserved; the LLM reads the `.md` version. The source summary links to the `.md` file.

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
date: YYYY-MM-DD          # Publication date of source
status: active | outdated
```

**Entity** (`wiki/entities/`):
```yaml
entity_type: person | organization | tool | album | book | framework
source_count: 0            # Number of sources referencing this entity
```

**Concept** (`wiki/concepts/`):
```yaml
confidence: high | medium | low
source_count: 0
```

**Comparison** (`wiki/comparisons/`):
```yaml
items: [item-a, item-b]    # What's being compared
```

**Howto** (`wiki/howtos/`):
```yaml
theme: cli-tools | mac | git | obsidian  # Cluster tag — reuse existing themes, add new ones as needed
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
Key takeaways from the comparison. What matters most depends on context.

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
2. Discuss key takeaways with the user — what stood out, what to emphasize
4. Create a source summary page in `wiki/sources/`
5. Identify entities mentioned — for each:
   - If the entity page exists: update it with new facts and increment `source_count`
   - If new: create the entity page
6. Identify concepts discussed — for each:
   - If the concept page exists: update it with new information, adjust `confidence` if warranted, increment `source_count`
   - If new: create the concept page
7. Add cross-references: link new pages to existing related pages, and update existing pages to link back
8. Update `wiki/index.md` with new entries
9. Update `wiki/overview.md` if the source meaningfully changes the big picture for its domain
10. Append to `wiki/log.jsonl`

### Query

When the user asks a question:

1. Read `wiki/index.md` to identify relevant pages
2. Read the relevant wiki pages
3. Synthesize an answer with `[[wikilinks]]` to sources
4. If the answer is substantial and reusable, ask the user if it should be filed as a new wiki page (concept, comparison, or entity)
5. If filed, update `wiki/index.md` and append to `wiki/log.jsonl`

### Delete

When the user wants to remove a source from the wiki:

1. Confirm with the user which source to delete
2. Read the source summary in `wiki/sources/` to identify all linked entity and concept pages
3. For each linked entity page:
   - Remove citations referencing the deleted source
   - Decrement `source_count`
   - If `source_count` reaches 0, delete the entity page
4. For each linked concept page:
   - Remove citations referencing the deleted source
   - Decrement `source_count`
   - If `source_count` reaches 0, delete the concept page
   - If remaining sources still support the concept, adjust `confidence` if warranted
5. Delete the source summary from `wiki/sources/`
6. Delete the raw source file from `raw/` (and its converted `.md` if applicable)
7. Remove deleted pages from `wiki/index.md` and update counts
8. Update `wiki/overview.md` if the deletion meaningfully changes the big picture
9. Append a `delete` operation to `wiki/log.jsonl`

### Lint

When the user asks for a health check:

1. Read `wiki/index.md` and scan all wiki pages
2. Check for:
   - Contradictions between pages
   - Stale claims superseded by newer sources
   - Orphan pages with no inbound links
   - Important concepts mentioned but lacking their own page
   - Missing cross-references between related pages
   - Entities or concepts with outdated `source_count`
   - Broken `[[wikilinks]]`
3. Report findings and fix them with user approval

## Rules

1. **Never modify files in `raw/`.** They are immutable source documents. The only exception is the Delete operation, which removes them entirely.
2. **Always use `[[wikilinks]]`** for internal references, never markdown links.
3. **Always update `wiki/index.md`** when creating or deleting pages.
4. **Always append to `wiki/log.jsonl`** after any operation.
5. **Cite sources.** Every factual claim on an entity or concept page must link to at least one source.
6. **Check `wiki/index.md` for existing pages** before creating new ones. Don't create duplicates.
7. **Check existing tags** in `wiki/index.md` before inventing new ones. Reuse when possible.
8. **Keep `source_count` accurate** on entity and concept pages.
9. **Use the correct domain** from the five defined domains. Don't invent new ones.
10. **Filenames are lowercase with hyphens.** No spaces, no underscores, no capitals.
11. **One entity/concept per page.** Don't combine multiple topics.
12. **Cross-reference aggressively.** If two pages are related, link them in both directions.

## Index Format

`wiki/index.md` uses this structure:

```markdown
# Wiki Index

Total pages: N | Sources: N | Entities: N | Concepts: N | Comparisons: N | Howtos: N

## Sources
| Page | Author | Domain | Date | Status |
|------|--------|--------|------|--------|
| [[source-name]] | Author | domain | YYYY-MM-DD | active |

## Entities
| Page | Type | Domain | Sources |
|------|------|--------|---------|
| [[entity-name]] | person | domain | 3 |

## Concepts
| Page | Domain | Confidence | Sources |
|------|--------|------------|---------|
| [[concept-name]] | domain | high | 5 |

## Comparisons
| Page | Domain | Items |
|------|--------|-------|
| [[comparison-name]] | domain | A vs B |

## Howtos
| Page | Theme | Domain |
|------|-------|--------|
| [[howto-name]] | cli-tools | domain |
```

## Log Format

`wiki/log.jsonl` is append-only. One JSON object per line:

```json
{"date":"YYYY-MM-DD","op":"ingest","desc":"Short description","source":"source-slug","created":["page-a","page-b"],"updated":["page-c"]}
```

Fields:
- `date` — ISO date
- `op` — one of: `ingest`, `query`, `lint`, `delete`, `update`, `create`
- `desc` — short description of what happened
- `source` — source slug (ingest/delete only, omit otherwise)
- `created` — list of page slugs created (omit if empty)
- `updated` — list of page slugs updated (omit if empty)
- `deleted` — list of page slugs deleted (omit if empty)

Query examples: `jq -s '.[-5:]' wiki/log.jsonl` (last 5 entries), `jq 'select(.op=="ingest")' wiki/log.jsonl` (all ingests).
