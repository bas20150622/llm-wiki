import json
from pathlib import Path

import pytest

from llm_wiki import SCHEMA_VERSION, cli
from llm_wiki.registry import load_registry, permission_path


def run(*argv):
    cli.main(list(argv))


def test_new_creates_and_registers_wiki(tmp_path, capsys):
    root = tmp_path / "work"
    run("new", "work", str(root), "--scope", "Work stuff", "--topic", "tech=Technology", "--topic", "consulting")

    assert load_registry() == {"work": root.resolve()}
    assert f"schema_version = {SCHEMA_VERSION}" in (root / "wiki.toml").read_text()
    claude_md = (root / "CLAUDE.md").read_text()
    assert "wiki: work" in claude_md and "@" in claude_md and "schema/CLAUDE.md" in claude_md
    assert json.loads((root / ".claude" / "settings.local.json").read_text()) == {"model": "sonnet"}
    index = (root / "wiki" / "index.md").read_text()
    assert "| tech | Technology | 0 |" in index and "| consulting | consulting | 0 |" in index
    for sub in ("sources", "entities", "concepts", "comparisons", "howtos", "notes", "templates", ".obsidian"):
        assert (root / "wiki" / sub).is_dir()
    assert "human:bas" in (root / "wiki" / "templates" / "note.md").read_text()


def test_new_without_topics_starts_with_empty_registry(tmp_path):
    from llm_wiki.lint import lint

    root = tmp_path / "blank"
    run("new", "blank", str(root), "--scope", "Starts empty")
    index = (root / "wiki" / "index.md").read_text()
    topics_section = index.split("## Topics")[1].split("## Sources")[0]
    assert topics_section.strip().splitlines() == ["| Topic | Description | Pages |", "|-------|-------------|-------|"]
    assert "No topics yet" in (root / "wiki" / "overview.md").read_text()
    assert lint(root) == []


def test_new_refuses_non_empty_directory(tmp_path):
    root = tmp_path / "busy"
    root.mkdir()
    (root / "file.txt").write_text("x")
    with pytest.raises(SystemExit) as exit_info:
        run("new", "busy", str(root), "--scope", "x", "--topic", "t")
    assert exit_info.value.code == 2


def test_permissions_deny_other_wikis_and_registry(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run("new", "a", str(a), "--scope", "A", "--topic", "t")
    run("new", "b", str(b), "--scope", "B", "--topic", "t")

    settings_a = json.loads((a / ".claude" / "settings.json").read_text())
    deny = settings_a["permissions"]["deny"]
    assert f"Read({permission_path(b)}/**)" in deny
    assert f"Edit({permission_path(b)}/**)" in deny
    assert not any(permission_path(a) in rule for rule in deny)
    assert "Bash(llm-wiki list:*)" in deny
    assert "Bash(llm-wiki convert:*)" in settings_a["permissions"]["allow"]


def test_permissions_cover_symlinked_spellings(tmp_path, monkeypatch):
    """A wiki reachable through a home-directory symlink is denied under both spellings."""
    home = tmp_path / "home"
    cloud = tmp_path / "cloud" / "Box"
    home.mkdir()
    cloud.mkdir(parents=True)
    (home / "Box").symlink_to(cloud)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    run("new", "a", str(tmp_path / "a"), "--scope", "A", "--topic", "t")
    run("new", "b", str(home / "Box" / "b"), "--scope", "B", "--topic", "t")

    deny = json.loads((tmp_path / "a" / ".claude" / "settings.json").read_text())["permissions"]["deny"]
    assert "Read(~/Box/b/**)" in deny
    assert f"Read({permission_path(cloud / 'b')}/**)" in deny


def test_sync_keeps_user_rules_and_does_not_duplicate(tmp_path):
    a = tmp_path / "a"
    run("new", "a", str(a), "--scope", "A", "--topic", "t")
    settings_path = a / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["permissions"]["allow"].append("Bash(git status)")
    settings_path.write_text(json.dumps(settings))

    run("sync-permissions")
    run("sync-permissions")
    allow = json.loads(settings_path.read_text())["permissions"]["allow"]
    assert "Bash(git status)" in allow
    assert allow.count("Bash(llm-wiki lint:*)") == 1


@pytest.mark.parametrize("command", [["list"], ["open", "a"], ["new", "x", "/tmp/x", "--scope", "s"], ["sync-permissions"]])
def test_registry_commands_refused_inside_session(monkeypatch, command, capsys):
    monkeypatch.setenv("LLM_WIKI_ACTIVE", "a")
    with pytest.raises(SystemExit) as exit_info:
        run(*command)
    assert exit_info.value.code == 2
    assert "not available inside a wiki session" in capsys.readouterr().err


def test_open_execs_agent_in_wiki_with_active_env(tmp_path, monkeypatch):
    a = tmp_path / "a"
    run("new", "a", str(a), "--scope", "A", "--topic", "t")
    calls = {}
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(cli.os, "execvpe", lambda file, argv, env: calls.update(file=file, argv=argv, env=env))
    monkeypatch.setattr(cli.os, "chdir", lambda path: calls.update(cwd=path))

    run("open", "a", "--continue")
    assert calls["cwd"] == a.resolve()
    assert calls["argv"] == ["claude", "--continue"]
    assert calls["env"]["LLM_WIKI_ACTIVE"] == "a"


def test_lint_refuses_other_wiki_inside_session(make_wiki, monkeypatch):
    other = make_wiki("other")
    monkeypatch.setenv("LLM_WIKI_ACTIVE", "alpha")
    with pytest.raises(SystemExit) as exit_info:
        run("lint", str(other))
    assert exit_info.value.code == 2


def test_convert_refuses_file_outside_active_wiki(make_wiki, tmp_path, monkeypatch):
    root = make_wiki("alpha")
    outside = tmp_path / "elsewhere.pdf"
    outside.write_bytes(b"%PDF")
    monkeypatch.chdir(root)
    monkeypatch.setenv("LLM_WIKI_ACTIVE", "alpha")
    with pytest.raises(SystemExit) as exit_info:
        run("convert", str(outside))
    assert exit_info.value.code == 2


def test_register_requires_matching_identity(make_wiki):
    root = make_wiki("alpha")
    with pytest.raises(SystemExit):
        run("register", "beta", str(root))
    run("register", "alpha", str(root))
    assert load_registry() == {"alpha": root.resolve()}
