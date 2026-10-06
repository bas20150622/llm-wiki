# LLM Wiki Schema

You are maintaining a personal knowledge wiki. You write and maintain all wiki pages except notes. The user curates sources, writes notes, and directs analysis. This file governs your behavior — read it fully before any operation.

## Wikis

This schema is shared by several strictly separated wikis. The engine (this schema plus the `llm-wiki` command) holds no wiki content. Each wiki is a directory elsewhere with:

- `wiki.toml` — identity read by the `llm-wiki` command: `name`, `user_id`, `schema_version`
- `CLAUDE.md` / `AGENTS.md` — the same identity for you, the wiki's scope, and its separation rules
- `.claude/settings.json` — permission rules, managed by `llm-wiki`, that block access to other wikis

`user_id` is the user's actor id for `generated.by` on notes (e.g. `human:bas`). All paths below (`raw/`, `wiki/`) are relative to the current wiki's root directory.

### Separation rules

1. **Operate on exactly one wiki:** the one whose `wiki.toml` is in the session's working directory or its nearest ancestor. If the session is not inside a wiki (for example, it runs in the engine repository), do not run wiki operations; ask the user to start a session with `llm-wiki open <name>`.
2. **Never read, write, search, link, or mention another wiki's content or location.** That covers `raw/`, `wiki/`, and logs, even when answering a question or when the content would be relevant.
3. **No wikilinks or paths that point outside the current wiki.**
4. **The only engine commands allowed in a wiki session are `llm-wiki convert` and `llm-wiki lint`.** Never run `llm-wiki open`, `list`, `new`, `register`, `unregister`, or `sync-permissions`; they reveal or change other wikis. The command also refuses them inside sessions started with `llm-wiki open`.
5. **Do not read the engine repository.** This schema reaches you through the import in the wiki's `CLAUDE.md`; nothing else in the engine is needed.

## Architecture

```
<wiki root>/
  wiki.toml              # Identity for the llm-wiki command
  CLAUDE.md, AGENTS.md   # Identity, scope, separation rules; CLAUDE.md imports this schema
  .claude/settings.json  # Permission rules managed by llm-wiki (do not edit the managed rules)
  raw/                   # Source documents — NEVER modify these
    assets/              # Images referenced by sources
  wiki/                  # The Obsidian vault
    sources/             # One summary per raw document (LLM-written)
    entities/            # People, orgs, tools, albums, books (LLM-written)
    concepts/            # Ideas, theories, frameworks (LLM-written)
    comparisons/         # Side-by-side analyses (LLM-written)
    howtos/              # Practical step-by-step guides (LLM-written)
    notes/               # Zettelkasten notes — written by the user only
    templates/           # Obsidian templates — not wiki pages; ignore in index and lint
    index.md             # Topic registry + content catalog — read this FIRST on every operation
    log.jsonl            # Append-only chronological record
    overview.md          # High-level synthesis, one section per topic

```

## Document Conversion

Non-markdown files in `raw/` (PDF, DOCX, PPTX, XLSX) must be converted to markdown before ingestion. Run from the wiki root:

```bash
llm-wiki convert raw/filename.pdf
```

This creates `raw/filename.md` alongside the original. The original binary is preserved; the LLM reads the `.md` version. The source summary links to the `.md` file in `source:` and to the original in `native_asset:`.

Supported formats: `.pdf`, `.docx`, `.pptx`, `.xlsx`

### Converted file format

A converted `.md` is a generated artifact that records where it came from:

```yaml
---
type: converted-source
converted_from: "filename.pdf"      # Native file in the same directory
source_sha256: "<hash>"             # SHA-256 of the native file at conversion time
converted_at: "YYYY-MM-DDTHH:MM:SSZ"
converted_by: "docling/<version>"
---
```

The body carries location markers so claims can be traced into the original: `<!-- page N -->` (PDF), `<!-- slide N -->` (PPTX), `<!-- sheet N: Name -->` (XLSX). DOCX has no fixed pagination and gets no markers. When a source summary attributes a claim, cite the location (e.g. "slide 12") where a marker exists.

### Overwrite behavior

- Existing `.md` matches the native file's hash: the script skips ("Up to date").
- Native file changed since conversion, or the existing `.md` was not made by the script (hand-written, or a stem collision such as `report.pdf` and `report.docx`): the script refuses and exits with code 2.
- `--force` overwrites. Never pass `--force` without the user's approval; the existing `.md` may hold hand edits.

## Topics

Each wiki has its own topic registry: the `## Topics` table at the top of `wiki/index.md`. Topics are added as the wiki grows; there is no fixed list.

- Every page has exactly one `topic` from the registry. Use `tags` for anything cross-cutting.
- Topic names are lowercase and hyphenated (e.g. `industrial-data`, `music-theory`).
- **Adding a topic:** when no registered topic fits a new source or page, propose a topic name and one-line description to the user. Only after approval, add a row to the registry and a section to `wiki/overview.md`, and log it as a `create` operation.
- **Never assign an unregistered topic**, and never add a topic without approval.

## Naming Conventions

- Filenames: lowercase, hyphens, no spaces (e.g., `modal-interchange.md`)
- Source summaries match raw filenames: `raw/karpathy-llm-wiki.md` -> `wiki/sources/karpathy-llm-wiki.md`
- Use `[[wikilinks]]` everywhere, never markdown links for internal pages

## Frontmatter Schema

Every wiki page has YAML frontmatter. Common fields:

```yaml
---
type: source | entity | concept | comparison | howto | note | overview
title: Human-readable title
topic: <registered-topic>
tags: [lowercase-hyphenated-tags]
last_updated: YYYY-MM-DD
generated:
  by: <tool>/<model-id>     # e.g. claude/claude-opus-5-5; the wiki's user_id for notes
  at: YYYY-MM-DD
stale_after: YYYY-MM-DD     # Optional. Set when claims are time-sensitive
---
```

### Provenance fields

Modeled on the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (OKF) provenance fields.

- `generated` — who produced the page content and when. Set it when you create a page. Update it when you substantially rewrite a page.
- `stale_after` — set it for claims that go out of date (product features, pricing, versions, org structure). Skip it for stable concepts.
- Pages without `generated` predate this schema. Do not backfill them with guessed values; add the field when you next substantially edit the page.

### Type-specific fields

**Source** (`wiki/sources/`):
```yaml
source: "[[raw/filename.md]]"          # The markdown file you read
native_asset: "[[raw/filename.pdf]]"   # Original file, if converted. Omit for natively markdown sources
author: Author Name
date: YYYY-MM-DD          # Publication date of source
status: active | outdated
```

**Entity** (`wiki/entities/`):
```yaml
entity_type: person | organization | tool | album | book | framework
sources: ["[[source-1]]", "[[source-2]]"]   # Every source page cited on this page
source_count: 2            # Number of sources referencing this entity. Must equal len(sources)
```

**Concept** (`wiki/concepts/`):
```yaml
confidence: high | medium | low
sources: ["[[source-1]]", "[[source-2]]"]   # Every source page cited on this page
source_count: 2            # Must equal len(sources)
```

**Comparison** (`wiki/comparisons/`):
```yaml
items: [item-a, item-b]    # What's being compared
```

**Howto** (`wiki/howtos/`):
```yaml
theme: cli-tools | mac | git | obsidian  # Cluster tag — reuse existing themes, add new ones as needed
```

**Note** (`wiki/notes/`):
```yaml
generated:
  by: human:<id>           # The wiki's user_id. A note drafted by an LLM keeps the LLM as author until the user rewrites it
  at: YYYY-MM-DD
continues: "[[note-x]]"    # Optional. The note this one branches from (Luhmann-style sequence)
```

## Notes (Zettelkasten)

Notes hold the user's own thinking: one idea per note, in the user's words. They are the only pages the LLM does not write.

- **Never create, rewrite, or edit the body of a note.** You may fix a note's frontmatter or a broken link only when the user asks.
- If the user asks you to draft a note, write it with `generated.by` set to your model. It becomes a human note only when the user rewrites it and changes `generated.by` themselves.
- Notes do not need source citations (exception to rule 5). They may cite wiki pages.
- Notes are exempt from rule 12: link from your pages to relevant notes, but never edit a note to add a link back. Obsidian's backlinks pane shows the reverse direction.
- Treat a note as the user's position. When a source contradicts a note, tell the user; do not resolve or "fix" the contradiction.

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
Original: [[raw/filename.pdf]]   <!-- only if converted; matches `native_asset` -->
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

## Related Notes
- [[note-name]] — what the user's note says about this concept (omit section if none)

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

### Note (written by the user)

```markdown
One idea, in the user's own words. Roughly 250 words at most.

## Links
- [[page-or-note]] — why this connects
```

## Operations

### Ingest

When the user adds a new source to `raw/` and asks you to process it:

1. If the source is a non-markdown file (PDF, DOCX, PPTX, XLSX), convert it first (see Document Conversion). Then proceed with the generated `.md` file. If the script refuses to overwrite, report why and ask the user before using `--force`.
2. Read the source document fully. For a converted file, read its frontmatter: `converted_from` becomes `native_asset` on the source summary.
3. Discuss key takeaways with the user — what stood out, what to emphasize. Name the registered topic the source belongs to, or propose a new one (see Topics).
4. Create a source summary page in `wiki/sources/`. Set `topic` and `generated`, and set `native_asset` if the source was converted.
5. Identify entities mentioned — for each:
   - If the entity page exists: update it with new facts, add the source to `sources`, and increment `source_count`
   - If new: create the entity page
6. Identify concepts discussed — for each:
   - If the concept page exists: update it with new information, add the source to `sources`, adjust `confidence` if warranted, increment `source_count`
   - If new: create the concept page
   - Set `generated` on every page you create or substantially rewrite; set `stale_after` for time-sensitive claims
7. Add cross-references: link new pages to existing related pages, and update existing pages to link back
8. Check `wiki/notes/` for notes related to the source. Link them from the relevant concept pages under `## Related Notes`. Tell the user if the source contradicts a note.
9. Update `wiki/index.md` with new entries and topic page counts
10. Update `wiki/overview.md` if the source meaningfully changes the big picture for its topic
11. Append to `wiki/log.jsonl`

### Query

When the user asks a question:

1. Read `wiki/index.md` to identify relevant pages, including notes
2. Read the relevant wiki pages
3. Synthesize an answer with `[[wikilinks]]` to sources. Keep the user's position, from notes ("your note says ..."), separate from what sources claim.
4. If the answer is substantial and reusable, ask the user if it should be filed as a new wiki page (concept, comparison, or entity)
5. If filed, update `wiki/index.md` and append to `wiki/log.jsonl`

### Delete

When the user wants to remove a source from the wiki:

1. Confirm with the user which source to delete
2. Read the source summary in `wiki/sources/` to identify all linked entity and concept pages
3. For each linked entity page:
   - Remove citations referencing the deleted source
   - Remove the source from `sources`
   - Decrement `source_count`
   - If `source_count` reaches 0, delete the entity page
4. For each linked concept page:
   - Remove citations referencing the deleted source
   - Remove the source from `sources`
   - Decrement `source_count`
   - If `source_count` reaches 0, delete the concept page
   - If remaining sources still support the concept, adjust `confidence` if warranted
5. Delete the source summary from `wiki/sources/`
6. Delete the raw source file from `raw/` (and its converted `.md` if applicable)
7. Remove deleted pages from `wiki/index.md` and update counts
8. Update `wiki/overview.md` if the deletion meaningfully changes the big picture
9. Append a `delete` operation to `wiki/log.jsonl`

Never delete a note as part of a Delete operation. If a deleted page was linked from a note, tell the user which notes now have broken links.

### Lint

When the user asks for a health check:

1. Run the mechanical checks from the wiki root and read the result:
   ```bash
   llm-wiki lint --json
   ```
   They cover: frontmatter fields, broken and empty `[[wikilinks]]`, links pointing outside the wiki, topics missing from the registry and registry page counts, orphan pages, one-way links between entity/concept/comparison/howto pages, `source_count` vs the Sources section vs `sources` frontmatter vs body citations, missing `source:`/`native_asset:` targets in `raw/`, stale conversions (`source_sha256` mismatch) and converted sources lacking `native_asset`, `stale_after` dates in the past, pages missing `generated`, index rows vs pages and the total count, notes with no links / over 250 words / not written by the user, non-markdown files in the vault, and invalid `log.jsonl` lines. Do not repeat these checks by hand.
2. Read `wiki/index.md` and the wiki pages (skip `wiki/templates/`) for the judgment checks the command cannot do:
   - Contradictions between pages
   - Stale claims superseded by newer sources
   - Important concepts mentioned but lacking their own page
   - Missing cross-references between pages that are related but not yet linked
   - Notes that contradict a source (keep the contradiction; just report it)
3. Report both sets of findings and fix them with user approval. Never edit a note as a fix. Do not reconvert a stale conversion without user approval.

## Rules

1. **Never modify files in `raw/`.** They are immutable source documents. The only exceptions are the Delete operation, which removes them entirely, and `llm-wiki convert`, which writes converted `.md` files next to the originals.
2. **Always use `[[wikilinks]]`** for internal references, never markdown links.
3. **Always update `wiki/index.md`** when creating or deleting pages.
4. **Always append to `wiki/log.jsonl`** after any operation.
5. **Cite sources.** Every factual claim on an entity or concept page must link to at least one source. Notes are exempt.
6. **Check `wiki/index.md` for existing pages** before creating new ones. Don't create duplicates.
7. **Check existing tags** in `wiki/index.md` before inventing new ones. Reuse when possible.
8. **Keep `source_count` accurate** on entity and concept pages. It must equal the length of `sources`.
9. **Use registered topics only.** Propose new topics to the user; never add or assign one without approval.
10. **Filenames are lowercase with hyphens.** No spaces, no underscores, no capitals.
11. **One entity/concept per page.** Don't combine multiple topics.
12. **Cross-reference aggressively.** If two pages are related, link them in both directions. Notes are exempt: link to them, never edit them.
13. **Keep wikis strictly separated.** See Separation rules.
14. **Never write or edit a note's body.** Notes are the user's own thinking.

## Index Format

`wiki/index.md` uses this structure:

```markdown
# Wiki Index

Wiki: <name> | Total pages: N | Sources: N | Entities: N | Concepts: N | Comparisons: N | Howtos: N | Notes: N

## Topics
| Topic | Description | Pages |
|-------|-------------|-------|
| topic-name | One-line description | 12 |

## Sources
| Page | Author | Topic | Date | Status |
|------|--------|-------|------|--------|
| [[source-name]] | Author | topic | YYYY-MM-DD | active |

## Entities
| Page | Type | Topic | Sources |
|------|------|-------|---------|
| [[entity-name]] | person | topic | 3 |

## Concepts
| Page | Topic | Confidence | Sources |
|------|-------|------------|---------|
| [[concept-name]] | topic | high | 5 |

## Comparisons
| Page | Topic | Items |
|------|-------|-------|
| [[comparison-name]] | topic | A vs B |

## Howtos
| Page | Theme | Topic |
|------|-------|-------|
| [[howto-name]] | cli-tools | topic |

## Notes
| Page | Topic | Last updated |
|------|-------|--------------|
| [[note-name]] | topic | YYYY-MM-DD |
```

Total pages counts content pages only (not `index.md`, `overview.md`, `log.jsonl`, or templates).

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

Log notes the user filed with a `create` entry the next time you run an operation and see them in `wiki/notes/` without an index row.

Query examples: `jq -s '.[-5:]' wiki/log.jsonl` (last 5 entries), `jq 'select(.op=="ingest")' wiki/log.jsonl` (all ingests).
