"""Tests for MEMORY.md and HISTORY.md persistence."""

from caveclaw import memory


def test_write_and_read_memory(tmp_path):
    memory.write_memory(tmp_path, "shopping list")
    assert memory.read_memory(tmp_path) == "shopping list"


def test_read_memory_nonexistent(tmp_path):
    assert memory.read_memory(tmp_path) == ""


def test_write_memory_creates_dirs(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    memory.write_memory(deep, "content")
    assert memory.read_memory(deep) == "content"


def test_write_memory_overwrites(tmp_path):
    memory.write_memory(tmp_path, "first")
    memory.write_memory(tmp_path, "second")
    assert memory.read_memory(tmp_path) == "second"


def test_append_and_read_history(tmp_path):
    memory.append_history(tmp_path, "event one")
    memory.append_history(tmp_path, "event two")
    text = memory.read_history(tmp_path)
    assert "event one" in text
    assert "event two" in text


def test_read_history_nonexistent(tmp_path):
    assert memory.read_history(tmp_path) == ""


def test_history_append_format(tmp_path):
    memory.append_history(tmp_path, "test event")
    text = memory.read_history(tmp_path)
    assert text.startswith("- [")
    assert "test event" in text
    assert text.endswith("\n")
