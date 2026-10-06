"""The llm-wiki command: open, create, and register wikis; convert sources; lint a wiki."""

import argparse
import os
import shutil
import sys
from pathlib import Path

from llm_wiki.registry import (
    ACTIVE_ENV,
    SCHEMA_DIR,
    WikiError,
    check_active,
    find_wiki_root,
    load_registry,
    read_identity,
    refuse_inside_session,
    save_registry,
    schema_warning,
    sync_permissions,
    validate_name,
)

AGENTS = ("claude", "codex")


def cmd_open(args) -> None:
    refuse_inside_session("open")
    wikis = load_registry()
    if args.name not in wikis:
        raise WikiError(f"Unknown wiki '{args.name}'. Registered: {', '.join(sorted(wikis)) or 'none'}.")
    root = wikis[args.name]
    identity = read_identity(root)
    warning = schema_warning(identity)
    if warning:
        print(f"Warning: {warning}", file=sys.stderr)
    if not shutil.which(args.agent):
        raise WikiError(f"`{args.agent}` is not on PATH.")
    os.chdir(root)
    env = {**os.environ, ACTIVE_ENV: args.name}
    os.execvpe(args.agent, [args.agent, *args.agent_args], env)


def cmd_list(args) -> None:
    refuse_inside_session("list")
    wikis = load_registry()
    if not wikis:
        print("No wikis registered. Create one with `llm-wiki new` or add one with `llm-wiki register`.")
    for name, root in sorted(wikis.items()):
        status = "ok" if (root / "wiki.toml").is_file() else "MISSING"
        print(f"{name:16} {status:8} {root}")


def parse_topics(values: list[str]) -> dict[str, str]:
    topics = {}
    for value in values:
        name, _, description = value.partition("=")
        validate_name(name)
        topics[name] = description.strip() or name
    return topics


def cmd_new(args) -> None:
    from llm_wiki.scaffold import create_wiki

    refuse_inside_session("new")
    validate_name(args.name)
    wikis = load_registry()
    if args.name in wikis:
        raise WikiError(f"A wiki named '{args.name}' is already registered at {wikis[args.name]}.")
    root = Path(args.path).expanduser().resolve()
    create_wiki(root, args.name, args.scope, args.user_id, parse_topics(args.topic))
    wikis[args.name] = root
    save_registry(wikis)
    sync_permissions(wikis)
    print(f"Created wiki '{args.name}' at {root}")
    print(f"Open it with: llm-wiki open {args.name}")
    print(f"Open {root / 'wiki'} as an Obsidian vault.")


def cmd_register(args) -> None:
    refuse_inside_session("register")
    validate_name(args.name)
    root = Path(args.path).expanduser().resolve()
    identity = read_identity(root)
    if identity.get("name") != args.name:
        raise WikiError(f"{root}/wiki.toml declares name '{identity.get('name')}', not '{args.name}'.")
    wikis = load_registry()
    wikis[args.name] = root
    save_registry(wikis)
    sync_permissions(wikis)
    print(f"Registered '{args.name}' at {root} and updated session permissions for all wikis.")


def cmd_unregister(args) -> None:
    refuse_inside_session("unregister")
    wikis = load_registry()
    if wikis.pop(args.name, None) is None:
        raise WikiError(f"Unknown wiki '{args.name}'.")
    save_registry(wikis)
    sync_permissions(wikis)
    print(f"Unregistered '{args.name}'. Its files are untouched.")


def cmd_sync_permissions(args) -> None:
    refuse_inside_session("sync-permissions")
    for path in sync_permissions(load_registry()):
        print(f"Updated {path}")


def cmd_convert(args) -> None:
    from llm_wiki.convert import convert

    path = Path(args.path)
    if os.environ.get(ACTIVE_ENV):
        root = find_wiki_root(Path.cwd())
        check_active(root)
        if not path.resolve().is_relative_to(root):
            raise WikiError(f"Refused: {path} is outside the current wiki.")
    convert(str(path), force=args.force)


def cmd_lint(args) -> None:
    from llm_wiki.lint import format_json, format_text, lint

    root = find_wiki_root(Path(args.path) if args.path else Path.cwd())
    check_active(root)
    findings = lint(root)
    print(format_json(findings) if args.json else format_text(findings))
    sys.exit(1 if any(f.severity == "error" for f in findings) else 0)


def cmd_schema(args) -> None:
    print(SCHEMA_DIR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-wiki", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("open", help="start an agent session inside a wiki")
    p.add_argument("--agent", choices=AGENTS, default="claude", help="agent to start (default: claude)")
    p.add_argument("name", help="registered wiki name")
    p.add_argument("agent_args", nargs=argparse.REMAINDER, help="arguments passed to the agent, e.g. --continue")
    p.set_defaults(func=cmd_open)

    p = sub.add_parser("list", help="list registered wikis")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("new", help="create and register a new wiki")
    p.add_argument("name")
    p.add_argument("path")
    p.add_argument("--scope", required=True, help="one-line description of what the wiki covers")
    p.add_argument("--topic", action="append", default=[], metavar='NAME="DESCRIPTION"', help="initial topic (repeatable, optional; topics can be added as the wiki grows)")
    p.add_argument("--user-id", default="human:bas", help="actor id for your notes (default: human:bas)")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("register", help="register an existing wiki directory")
    p.add_argument("name")
    p.add_argument("path")
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("unregister", help="remove a wiki from the registry (files are kept)")
    p.add_argument("name")
    p.set_defaults(func=cmd_unregister)

    p = sub.add_parser("sync-permissions", help="rewrite every wiki's .claude/settings.json separation rules")
    p.set_defaults(func=cmd_sync_permissions)

    p = sub.add_parser("convert", help="convert a PDF, DOCX, PPTX, or XLSX file in raw/ to markdown")
    p.add_argument("path")
    p.add_argument("--force", action="store_true", help="overwrite an existing .md even if stale or unmanaged")
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("lint", help="run the mechanical health checks on the current wiki")
    p.add_argument("path", nargs="?", help="any path inside the wiki (default: current directory)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("schema", help="print the schema directory")
    p.set_defaults(func=cmd_schema)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if not (SCHEMA_DIR / "CLAUDE.md").is_file():
        print(f"Engine schema not found at {SCHEMA_DIR}. Install the engine with `uv tool install --editable`.", file=sys.stderr)
        sys.exit(1)
    try:
        args.func(args)
    except WikiError as error:
        print(error, file=sys.stderr)
        sys.exit(2)
