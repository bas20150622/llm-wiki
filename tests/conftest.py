import pytest

from llm_wiki.scaffold import create_wiki


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Every test gets its own registry and runs outside a wiki session."""
    monkeypatch.setenv("LLM_WIKI_REGISTRY", str(tmp_path / "config" / "wikis.toml"))
    monkeypatch.delenv("LLM_WIKI_ACTIVE", raising=False)


@pytest.fixture
def make_wiki(tmp_path):
    def make(name="alpha", topics=None):
        root = tmp_path / name
        create_wiki(root, name, f"{name} test wiki", "human:test", {"tech": "Technology"} if topics is None else topics)
        return root

    return make


def write_page(root, kind, slug, frontmatter, body):
    path = root / "wiki" / kind / f"{slug}.md"
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n{body.strip()}\n", encoding="utf-8")
    return path
