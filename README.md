# LLM Wiki

A personal knowledge base maintained by LLMs, based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Instead of RAG (re-deriving knowledge every query), the LLM incrementally builds and maintains a persistent wiki of interlinked markdown files. Knowledge compounds over time — cross-references are already there, contradictions have been flagged, synthesis reflects everything you've read.

## How It Works

This repository is the **engine**: the shared schema and the `llm-wiki` command. It holds no wiki content. Each **wiki** is a separate directory, anywhere on disk, that the engine works on. Wikis are strictly separated from each other.

```
~/tools/llm-wiki/                 ENGINE (this repo): schema + llm-wiki command
~/.config/llm-wiki/wikis.toml     REGISTRY: wiki name -> directory (only the command reads it)

<wiki>/                           WIKI INSTANCE (one per wiki, e.g. work and private)
  wiki.toml                       identity: name, user_id, schema_version
  CLAUDE.md, AGENTS.md            identity + scope; CLAUDE.md imports the engine schema
  .claude/settings.json           permission rules that block the other wikis (managed)
  raw/                            your sources (immutable)
  wiki/                           the Obsidian vault: LLM pages + your notes
```

**Layers in each wiki:**

| Layer | Owner | Purpose |
|-------|-------|---------|
| `raw/` | You | Immutable source documents — articles, papers, clippings |
| `wiki/` | LLM | Generated pages — summaries, entities, concepts, comparisons, howtos |
| `wiki/notes/` | You | Your own Zettelkasten notes — the LLM links to them but never writes them |

**Operations** (run inside a wiki session):

- **Ingest** — drop a source in `raw/`, tell the LLM to process it. It writes a summary, creates/updates entity and concept pages, maintains cross-references, links your related notes, updates the index.
- **Query** — ask questions against the wiki. The LLM keeps your notes' position separate from what sources claim. Good answers get filed back as new pages.
- **Delete** — remove a source and cascade the cleanup through entity and concept pages. Notes are never deleted.
- **Lint** — `llm-wiki lint` runs the mechanical checks; the LLM adds judgment checks such as contradictions and missing concepts.

## Separation

Each session works on one wiki and cannot reach the others:

- **Storage:** the engine, each wiki, and the registry live in different places. Work content can stay on employer storage and private content on personal storage.
- **Session scope:** `llm-wiki open <name>` starts the agent inside that wiki with `LLM_WIKI_ACTIVE=<name>` set. Inside such a session, `llm-wiki convert` and `llm-wiki lint` refuse to touch any other wiki, and the registry commands (`open`, `list`, `new`, `register`, `unregister`, `sync-permissions`) refuse to run at all.
- **Permissions:** each wiki's `.claude/settings.json` denies Claude Code's file tools access to every other registered wiki and to the registry, and denies the registry commands. `llm-wiki sync-permissions` rewrites these rules; `new`, `register`, and `unregister` run it for you. Other rules you add to the file are kept.
- **Schema rules:** the shared schema tells the LLM never to read, link, or mention another wiki.
- **Limit:** permission rules cover Claude Code's file tools, not arbitrary shell commands. A shell command such as `cat` on another wiki's path is still possible if you approve it.

## Installation

Prerequisites: [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
git clone git@github.com:bas20150622/llm-wiki.git ~/tools/llm-wiki
uv tool install --editable ~/tools/llm-wiki
```

This puts `llm-wiki` on your PATH (in `~/.local/bin`). The install must be editable: the command reads the schema from the checkout. It installs [Docling](https://github.com/DS4SD/docling) for document conversion. On Linux, add `--extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match` to get CPU-only PyTorch.

Updating the engine for every wiki at once:
```bash
cd ~/tools/llm-wiki && git pull
```

## Usage

```bash
llm-wiki new work ~/Work/wiki --scope "Client work and technology" \
  --topic technology="Software and architecture" --topic consulting="Methods and industry analysis"
llm-wiki register private ~/Personal/wiki          # an existing wiki
llm-wiki list

llm-wiki open work                      # start Claude Code inside the wiki
llm-wiki open private --continue        # resume the last session in that wiki
llm-wiki open --agent codex work        # start Codex instead

# Inside a session (the LLM runs these):
llm-wiki convert raw/report.pdf         # PDF, DOCX, PPTX, XLSX -> markdown
llm-wiki lint                           # mechanical health checks (--json for machine output)
```

Run one session per wiki. Changing directory inside a session does not switch wikis; start a new session with `llm-wiki open`.

### Document conversion

`llm-wiki convert raw/my-report.pdf` creates `raw/my-report.md` next to the original. The converted file starts with provenance frontmatter (`converted_from`, `source_sha256`, `converted_at`, `converted_by`) and has `<!-- page N -->`, `<!-- slide N -->`, or `<!-- sheet N: Name -->` markers so claims can be traced into the original. DOCX has no fixed pages and gets no markers.

Re-running is safe: the command skips a file whose `.md` matches the original's SHA-256, and refuses (exit code 2) when the original changed or the `.md` was not made by it (hand-written, or a name clash such as `report.pdf` and `report.docx`). `--force` overwrites; check for hand edits first.

### Obsidian

Each wiki's `wiki/` directory is its own vault: "Open folder as vault" and select it. Keep one vault per wiki. The **Templates** core plugin points at `templates/`; insert `templates/note.md` to start a note. Recommended: the **Dataview** plugin and the **Obsidian Web Clipper** browser extension.

### Claude Code

`llm-wiki open <name>` is the normal way in. Claude Code loads the wiki's `CLAUDE.md`, which imports `schema/CLAUDE.md` from the engine; it asks once per wiki to approve that external import. Each wiki's `.claude/settings.local.json` sets the model to `sonnet` (the current default Sonnet); change it per wiki or override with `/model`.

A session in the engine repository is for developing the engine (see `CLAUDE.md` there). It refuses wiki operations.

### Codex

`llm-wiki open --agent codex <name>`. Codex reads the wiki's `AGENTS.md`, which points it at `schema/AGENTS.md` (identical to `schema/CLAUDE.md`).

### ChatGPT (web UI)

1. Copy everything below the `---` line in `schema/chatgpt-instructions.md`
2. Paste into Custom Instructions, a Custom GPT system prompt, or the start of a conversation
3. Use a separate ChatGPT Project per wiki, so chat history and memory don't mix them

ChatGPT cannot write files — it outputs markdown blocks that you copy into the wiki.

## Topics

Each wiki has its own topic registry: the `## Topics` table at the top of `wiki/index.md`. Every page has one `topic`; tags cover anything cross-cutting. When a new source fits no registered topic, the LLM proposes one and adds it only after you approve. You can also ask directly ("add a topic for data governance").

Filter by topic in Dataview:
```
TABLE title, source_count FROM "concepts" WHERE topic = "technology"
```

## Notes (Zettelkasten)

`wiki/notes/` is where your own thinking goes: one idea per note, in your own words, about 250 words at most. Every other page is the LLM's synthesis of sources; notes are your position.

- Start a note from `templates/note.md`. It sets `type: note` and `generated.by` to your user id.
- End each note with `## Links`, giving a reason for every link (`- [[page]] — why this connects`).
- Use `continues: "[[other-note]]"` in frontmatter to branch from an earlier note.
- The LLM never writes or edits a note. It links concept pages to your notes, tells you when a source contradicts one, and keeps "your note says" separate from "sources say".
- Notes need no source citations.

## Provenance

The schema borrows provenance fields from Google's [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (OKF), without adopting the rest of it. The wiki keeps `[[wikilinks]]` and `log.jsonl`, where OKF uses markdown links and a prose `log.md`.

- `generated` — which tool and model wrote the page, and when (your user id for notes)
- `stale_after` — optional date after which time-sensitive claims need a recheck
- `native_asset` on source pages — the original PDF, DOCX, PPTX, or XLSX of a converted source
- `sources` on entity and concept pages — every cited source, checked against `source_count`

## Schema versions

Each wiki's `wiki.toml` declares the `schema_version` it follows. `llm-wiki open` and `llm-wiki lint` warn when it differs from the engine. `schema/CHANGELOG.md` lists each version's migration steps.

## Development

See `CLAUDE.md`. In short: `uv tool install --editable . --with pytest`, then `"$(uv tool dir)/llm-wiki/bin/python" -m pytest -q`.
