"""The wiki registry, wiki identity files, and the guards that keep wiki sessions separated.

The registry (~/.config/llm-wiki/wikis.toml) is the only place that knows where every wiki lives.
Commands that reveal or change it refuse to run inside a wiki session started with `llm-wiki open`.
"""

import json
import os
import re
import tomllib
from pathlib import Path

from llm_wiki import SCHEMA_VERSION

ACTIVE_ENV = "LLM_WIKI_ACTIVE"
IDENTITY_FILE = "wiki.toml"
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

ENGINE_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ENGINE_ROOT / "schema"


class WikiError(Exception):
    """A refusal or usage error, reported to the user without a traceback."""


def registry_path() -> Path:
    override = os.environ.get("LLM_WIKI_REGISTRY")
    return Path(override) if override else Path.home() / ".config" / "llm-wiki" / "wikis.toml"


def load_registry() -> dict[str, Path]:
    path = registry_path()
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {name: Path(entry["path"]) for name, entry in data.get("wikis", {}).items()}


def save_registry(wikis: dict[str, Path]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Managed by llm-wiki. Maps wiki names to their root directories.", ""]
    for name, root in sorted(wikis.items()):
        # json.dumps output is a valid TOML basic string.
        lines += [f"[wikis.{name}]", f"path = {json.dumps(str(root))}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def validate_name(name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise WikiError(f"Invalid wiki name '{name}': use lowercase letters, digits, and hyphens, starting with a letter.")


def refuse_inside_session(command: str) -> None:
    """Registry commands reveal other wikis' locations, so a wiki session may not run them."""
    active = os.environ.get(ACTIVE_ENV)
    if active:
        raise WikiError(
            f"Refused: `llm-wiki {command}` is not available inside a wiki session (active wiki: {active}). "
            "Run it from a normal terminal."
        )


def read_identity(root: Path) -> dict:
    path = root / IDENTITY_FILE
    if not path.is_file():
        raise WikiError(f"{root} is not a wiki: {IDENTITY_FILE} not found.")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def find_wiki_root(start: Path) -> Path:
    """Walk up from `start` to the nearest directory containing wiki.toml."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / IDENTITY_FILE).is_file():
            return candidate
    raise WikiError(f"Not inside a wiki: no {IDENTITY_FILE} in {current} or its parents.")


def check_active(root: Path) -> None:
    """Inside a session, only the session's own wiki may be touched."""
    active = os.environ.get(ACTIVE_ENV)
    if active and read_identity(root).get("name") != active:
        raise WikiError(f"Refused: this session belongs to wiki '{active}'; {root} is a different wiki.")


def schema_warning(identity: dict) -> str | None:
    found = identity.get("schema_version")
    if found != SCHEMA_VERSION:
        return (
            f"Wiki '{identity.get('name')}' declares schema_version {found}, engine is {SCHEMA_VERSION}. "
            "See schema/CHANGELOG.md and update the wiki."
        )
    return None


def permission_path(path: Path) -> str:
    """Path in Claude Code permission-rule syntax: ~/... under home, //absolute otherwise. Symlinks are kept."""
    path = path.absolute()
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return "/" + path.as_posix()


def path_aliases(path: Path) -> list[Path]:
    """The real path plus every spelling of it through a symlink in the home directory.

    Cloud folders are often reachable both ways (~/Dropbox -> ~/Library/CloudStorage/Dropbox), and a deny
    rule only blocks the spelling it names.
    """
    real = path.resolve()
    aliases = {path.absolute(), real}
    for entry in Path.home().iterdir():
        if entry.is_symlink():
            target = entry.resolve()
            if real.is_relative_to(target):
                aliases.add(entry / real.relative_to(target))
    return sorted(aliases)


# Registry-revealing commands are denied in every wiki session, in addition to the environment guard.
SESSION_ALLOWED = ["Bash(llm-wiki convert:*)", "Bash(llm-wiki lint:*)"]
SESSION_DENIED_COMMANDS = [
    f"Bash(llm-wiki {command}:*)" for command in ("open", "list", "new", "register", "unregister", "sync-permissions")
]


def sync_permissions(wikis: dict[str, Path]) -> list[Path]:
    """Write each wiki's .claude/settings.json so its sessions cannot touch the other wikis or the registry.

    Rules this tool manages are replaced; any other rules in the file are kept.
    """
    registry_rules = [permission_path(p) for p in path_aliases(registry_path().parent)]
    wiki_rules = {name: [permission_path(p) for p in path_aliases(root)] for name, root in wikis.items()}
    all_rules = registry_rules + [rule for rules in wiki_rules.values() for rule in rules]

    def managed(rule: str) -> bool:
        return "llm-wiki" in rule or any(p in rule for p in all_rules)

    written = []
    for name, root in wikis.items():
        if not root.is_dir():
            continue
        settings_path = root / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
        permissions = settings.setdefault("permissions", {})
        allow = [r for r in permissions.get("allow", []) if not managed(r)]
        deny = [r for r in permissions.get("deny", []) if not managed(r)]

        allow += SESSION_ALLOWED
        deny += SESSION_DENIED_COMMANDS
        others = [rule for other, rules in sorted(wiki_rules.items()) if other != name for rule in rules]
        for target in registry_rules + others:
            deny += [f"Read({target}/**)", f"Edit({target}/**)"]

        permissions["allow"], permissions["deny"] = allow, deny
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        written.append(settings_path)
    return written
