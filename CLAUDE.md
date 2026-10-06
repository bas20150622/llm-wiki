# LLM Wiki Engine — Development

This repository is the engine for LLM-maintained wikis: the shared schema and the `llm-wiki` command. It holds no wiki content. Sessions here are for developing the engine, never for wiki operations.

## Rules

- **No wiki content in this repository.** Never create, copy, or move wiki pages, `raw/` sources, or notes into it. `.gitignore` blocks `raw/` and `wiki/` directories as a backstop.
- **Never read the wikis.** Do not open registered wiki directories or `~/.config/llm-wiki/wikis.toml` while developing. Test against temporary wikis built by the test fixtures.
- **Never run `llm-wiki open`** from a development session.

## Layout

```
schema/                   # The wiki schema, imported by each wiki's CLAUDE.md
  CLAUDE.md               # Source of truth
  AGENTS.md               # Identical copy for Codex — after editing CLAUDE.md: cp schema/CLAUDE.md schema/AGENTS.md
  chatgpt-instructions.md # Condensed version for ChatGPT; update by hand
  CHANGELOG.md            # One entry per SCHEMA_VERSION
llm_wiki/
  __init__.py             # SCHEMA_VERSION
  cli.py                  # Subcommands: open, list, new, register, unregister, sync-permissions, convert, lint, schema
  registry.py             # Registry file, wiki.toml identity, session guards, permission rules
  scaffold.py             # Creating wikis and writing identity files
  templates/              # *.tmpl files for new wikis and the Obsidian config
  convert.py              # Docling conversion with provenance frontmatter and location markers
  lint.py                 # Mechanical lint checks
tests/                    # pytest; fixtures build throwaway wikis in tmp_path
```

## Working on the engine

- Install (editable, so the `llm-wiki` command runs this checkout):
  ```bash
  uv tool install --editable . --with pytest
  ```
- Test:
  ```bash
  "$(uv tool dir)/llm-wiki/bin/python" -m pytest -q              # all tests (includes one slow real conversion)
  "$(uv tool dir)/llm-wiki/bin/python" -m pytest -q -m "not slow"
  ```
- Changing the schema in a way wikis must follow: bump `SCHEMA_VERSION`, add a `schema/CHANGELOG.md` entry with migration steps, sync `schema/AGENTS.md`, and update `chatgpt-instructions.md`.
- Changing which commands wiki sessions may run: update `SESSION_ALLOWED` / `SESSION_DENIED_COMMANDS` in `registry.py`, then run `llm-wiki sync-permissions` from a normal terminal.
- After adding a dependency, rerun the install command.
