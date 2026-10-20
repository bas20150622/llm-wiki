# TODO

Known gaps and open ideas for the engine and schema. Each item says what is missing and why it matters.

## Source naming (schema 3)

- **Lint does not check directory names.** The schema says directories under `raw/` follow the filename rules (lowercase, hyphens, no spaces), but nothing enforces it. A directory like `ML Course/` gives a source page name with spaces and capitals. Add a lint warning for `raw/` path components that break the rules.
- **Long source names.** `raw/ml-course/module-1.md` becomes `ml-course-module-1`, and every wikilink and index row carries the full name. Deeply nested directories make it worse. Consider a depth limit, or an optional `title` for display in the index.

## Source granularity

- **One summary per raw file.** A multi-file source (a course, a book split into chapters) gets one summary per file, so `source_count` counts files rather than sources and the index fills with entries like `course-intro` and `course-toc`. Options:
  - A book-level summary whose `source:` frontmatter lists every file. Lint already accepts a list in `source:` and checks each target exists. The schema needs an exception to the one-summary-per-raw-file rule, plus rules for `native_asset`.
  - A grouping field (for example `collection: ml-course`) so the index and queries can treat the files as one source.

## Change detection

- **Native markdown has no `source_sha256`.** Converted files record a hash and lint flags stale conversions. A markdown source edited after ingest, in `raw/` or in a symlinked original, leaves the summary stale with no warning. Options: record the hash in the source summary's frontmatter at ingest, and have lint compare it to the raw file.
- **Symlinked sources** make this worse. The original can change, move or disappear outside the wiki. A dangling link is reported as a missing `source:` target, but a changed target is not reported.

## Symlinked sources

- **`llm-wiki convert` refuses symlinks that point outside the wiki** inside a session. `cmd_convert` checks `path.resolve().is_relative_to(root)`, and `resolve()` follows the link. This only affects PDF, DOCX, PPTX and XLSX. Running convert from a normal terminal works. If it becomes common, check the link's lexical location (inside `raw/`) instead of the resolved path.
- **Read permissions.** Claude Code checks the resolved path, so reading a symlinked source from outside the wiki may prompt each time. The workaround is a `Read(<source repo>/**)` allow rule in the wiki's `.claude/settings.json`. Check that `llm-wiki sync-permissions` keeps it. It should, because it only replaces rules it manages. Document this in the README.
- **Lint does not follow symlinked directories.** `rglob` skips them on Python before 3.13, so a directory symlink in `raw/` is not scanned for source-name collisions. File symlinks are fine. Recommend one symlink per file, or document the limit.

## Mixed sources on one topic

- **No source kind.** A book, a course and research notes on the same topic look the same in the index. Consider a `source_kind` field (`book`, `course`, `research`, ...) on source pages, or a recommended `tags` convention.
- **Concept pages merge sources.** Attribution survives only through inline citations, and `confidence` is per page. Querying "only from source X" depends on the LLM filtering citations.
- **Query has no scoped mode.** Add a query step for restricting an answer to named sources, with per-claim attribution, and say what to do when a summary is too thin and the raw file is needed.
