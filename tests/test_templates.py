"""Tests that agent templates exist and contain expected content."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"


def test_claw_soul_exists():
    assert (AGENTS_DIR / "claw" / "SOUL.md").is_file()


def test_claw_soul_content():
    content = (AGENTS_DIR / "claw" / "SOUL.md").read_text()
    assert "Claw" in content


def test_shadow_soul_exists():
    assert (AGENTS_DIR / "shadow" / "SOUL.md").is_file()


def test_grocer_soul_exists():
    assert (AGENTS_DIR / "grocer" / "SOUL.md").is_file()


def test_grocer_soul_has_personality():
    content = (AGENTS_DIR / "grocer" / "SOUL.md").read_text()
    assert "## Personality" in content


def test_grocer_soul_has_list_format():
    content = (AGENTS_DIR / "grocer" / "SOUL.md").read_text()
    assert "## List Format" in content


def test_grocer_soul_has_data_logging():
    content = (AGENTS_DIR / "grocer" / "SOUL.md").read_text()
    assert "## Data Logging" in content


def test_grocer_tools_exists():
    assert (AGENTS_DIR / "grocer" / "TOOLS.md").is_file()


def test_grocer_tools_mentions_sqlite():
    content = (AGENTS_DIR / "grocer" / "TOOLS.md").read_text()
    assert "SQLite" in content


def test_all_agents_have_soul():
    for agent_dir in AGENTS_DIR.iterdir():
        if agent_dir.is_dir():
            assert (agent_dir / "SOUL.md").is_file(), f"{agent_dir.name} missing SOUL.md"
