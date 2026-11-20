# Schema Changelog

A wiki's `wiki.toml` declares the `schema_version` it follows. `llm-wiki open` and `llm-wiki lint` warn when it differs from the engine's version. When the schema changes, bump `SCHEMA_VERSION` in `llm_wiki/__init__.py`, add an entry here with the migration steps, and update each wiki.

## 4 — 2026-11-17

- The index has two levels. `wiki/index.md` keeps the totals line and the topic registry, which gains an `Index` column linking each topic's catalog. The page tables move to one catalog per topic, `wiki/index-<topic>.md`, without the Topic column. Operations read the registry first and then only the catalogs they need. Lint checks each page against the catalog of its topic and runs its judgment checks one topic at a time.
- A source summary is tied to its raw file by `source:` alone, which holds the exact raw path (spaces, capitals, and underscores included). The summary's name is a readable label and no longer has to match the raw path; `raw/` names are unrestricted. Lint drops the "should be named" warning and the name collision error, and instead reports two source pages for the same raw file (error) and a source page without exactly one raw `source:` (warning).
- Duplicate check: before creating a page, look for its file on disk, since it may be catalogued under another topic. Tags are looked up in the pages of the same topic.
- Migration: from a normal terminal, run `llm-wiki split-index <wiki root>` (or `llm-wiki split-index` from inside the wiki). It moves every table row into the catalog of its Topic column, rebuilds the registry, keeps any other sections of `index.md`, sets `schema_version = 4` in `wiki.toml`, `CLAUDE.md`, and `AGENTS.md`, and logs an `update`. It refuses, and writes nothing, if a row's topic is not in the registry or a topic name is not lowercase and hyphenated. Page files are not renamed. Then run `llm-wiki lint`. Run `llm-wiki sync-permissions` once so sessions may run `split-index`.

## 3 — 2026-10-20

- Source summaries are named after the raw file's path: directories under `raw/` joined to the filename stem with hyphens (`raw/course/module-1.md` -> `wiki/sources/course-module-1.md`). Files directly in `raw/` keep their stem, so existing wikis need no renames. Migration: set `schema_version = 3` in `wiki.toml` and in the `schema_version:` line of `CLAUDE.md` and `AGENTS.md`.
- Lint reports raw markdown files that map to the same source page name (error) and source pages not named after their `source:` path (warning).

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
