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
  index.md               # Content catalog — read this FIRST on every operation
  log.md                 # Append-only chronological record
  overview.md            # High-level synthesis across all domains
```

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
type: source | entity | concept | comparison | overview
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

## Operations

### Ingest

When the user adds a new source to `raw/` and asks you to process it:

1. Read the source document fully
2. Discuss key takeaways with the user
3. Create a source summary page in `wiki/sources/`
4. Identify entities — create or update entity pages, maintain `source_count`
5. Identify concepts — create or update concept pages, adjust `confidence` and `source_count`
6. Add cross-references in both directions between related pages
7. Update `wiki/index.md` with new entries
8. Update `wiki/overview.md` if the source meaningfully changes the big picture
9. Append to `wiki/log.md`

### Query

When the user asks a question:

1. Read `wiki/index.md` to identify relevant pages
2. Read the relevant wiki pages
3. Synthesize an answer with `[[wikilinks]]` to sources
4. If the answer is substantial and reusable, offer to file it as a new wiki page
5. If filed, update `wiki/index.md` and append to `wiki/log.md`

### Lint

When the user asks for a health check:

1. Read `wiki/index.md` and scan all wiki pages
2. Check for: contradictions, stale claims, orphan pages, missing concept pages, missing cross-references, outdated `source_count`, broken `[[wikilinks]]`
3. Report findings and fix with user approval

## Rules

1. **Never modify files in `raw/`.**
2. **Always use `[[wikilinks]]`** for internal references.
3. **Always update `wiki/index.md`** when creating or deleting pages.
4. **Always append to `wiki/log.md`** after any operation.
5. **Cite sources.** Every factual claim must link to at least one source.
6. **Check `wiki/index.md` for existing pages** before creating new ones.
7. **Reuse existing tags** — check before inventing new ones.
8. **Keep `source_count` accurate.**
9. **Use defined domains only.** Don't invent new ones.
10. **Filenames: lowercase, hyphens.** No spaces, underscores, or capitals.
11. **One entity/concept per page.**
12. **Cross-reference aggressively.** Link related pages in both directions.

## Index Format

`wiki/index.md` uses markdown tables with sections for Sources, Entities, Concepts, Comparisons. Each row has a wikilink plus key metadata. A summary line at the top shows total counts.

## Log Format

`wiki/log.md` is append-only. Format: `## [YYYY-MM-DD] operation | description` followed by affected pages as wikilinks. Operations: `ingest`, `query`, `lint`, `update`, `create`.
