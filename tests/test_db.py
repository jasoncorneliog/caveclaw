"""Tests for SQLite state and scheduled tasks."""

import pytest

import caveclaw.db as db_mod


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch, tmp_path):
    """Redirect DB_PATH to a temp file for every test."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")


def test_init_db_creates_tables():
    db_mod.init_db()
    db_mod.set_state("test_key", "test_value")
    assert db_mod.get_state("test_key") == "test_value"


def test_set_and_get_state():
    db_mod.init_db()
    db_mod.set_state("color", "blue")
    assert db_mod.get_state("color") == "blue"


def test_get_state_default():
    db_mod.init_db()
    assert db_mod.get_state("missing") is None
    assert db_mod.get_state("missing", "fallback") == "fallback"


def test_set_state_upsert():
    db_mod.init_db()
    db_mod.set_state("key", "v1")
    db_mod.set_state("key", "v2")
    assert db_mod.get_state("key") == "v2"


def test_add_task_returns_id():
    db_mod.init_db()
    task_id = db_mod.add_task("buy milk", "0 9 * * *", "echo buy milk")
    assert isinstance(task_id, int)
    assert task_id > 0


def test_get_due_tasks_returns_enabled():
    db_mod.init_db()
    db_mod.add_task("task1", "* * * * *", "cmd1")
    db_mod.add_task("task2", "0 * * * *", "cmd2")
    tasks = db_mod.get_due_tasks()
    assert len(tasks) == 2
    assert tasks[0]["name"] == "task1"
    assert tasks[1]["name"] == "task2"


def test_get_due_tasks_empty():
    db_mod.init_db()
    assert db_mod.get_due_tasks() == []
