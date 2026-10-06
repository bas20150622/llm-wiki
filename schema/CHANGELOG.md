# Schema Changelog

A wiki's `wiki.toml` declares the `schema_version` it follows. `llm-wiki open` and `llm-wiki lint` warn when it differs from the engine's version. When the schema changes, bump `SCHEMA_VERSION` in `llm_wiki/__init__.py`, add an entry here with the migration steps, and update each wiki.

## 2 — 2026-10-06

- Engine and wikis separated: the engine holds no content; wikis declare identity in `wiki.toml`.
- `domain` replaced by `topic`, with a per-wiki topic registry in `index.md`. Migration: rename the field on every page; add the `## Topics` table.
- New page type `note` in `wiki/notes/` (Zettelkasten, written by the user only). Migration: create `wiki/notes/` and `wiki/templates/note.md`; add a `## Notes` table and a `Notes:` count to `index.md`.
- Provenance fields `generated` and `stale_after`; entity and concept pages list cited sources in a `sources` frontmatter list. Migration: none required; lint reports pages missing `generated` and `sources`.
- `verified` removed.
- Conversion runs through `llm-wiki convert`; converted files carry provenance frontmatter and page/slide/sheet markers.
- Lint runs `llm-wiki lint` for the mechanical checks.

## 1

- Original schema: fixed domains, `scripts/convert.py` run from the repository root.
