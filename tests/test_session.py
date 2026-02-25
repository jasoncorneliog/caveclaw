"""Tests for JSONL session persistence."""

import json

from caveclaw import session


def test_get_or_create_creates_file(tmp_path):
    sessions_dir = tmp_path / "sessions"
    path = session.get_or_create("chat1", sessions_dir)
    assert path.exists()
    assert path.parent == sessions_dir


def test_append_writes_jsonl(tmp_path):
    sessions_dir = tmp_path / "sessions"
    session.append("chat1", "user", "hello", sessions_dir=sessions_dir)
    path = sessions_dir / "chat1.jsonl"
    line = json.loads(path.read_text().strip())
    assert line["role"] == "user"
    assert line["content"] == "hello"
    assert "ts" in line


def test_append_with_attachments(tmp_path):
    sessions_dir = tmp_path / "sessions"
    att = [{"filename": "pic.png", "path": "/tmp/pic.png", "content_type": "image/png", "size": 100}]
    session.append("chat1", "user", "see image", sessions_dir=sessions_dir, attachments=att)
    path = sessions_dir / "chat1.jsonl"
    line = json.loads(path.read_text().strip())
    assert line["attachments"] == att


def test_append_without_attachments_omits_key(tmp_path):
    sessions_dir = tmp_path / "sessions"
    session.append("chat1", "user", "hi", sessions_dir=sessions_dir)
    path = sessions_dir / "chat1.jsonl"
    line = json.loads(path.read_text().strip())
    assert "attachments" not in line


def test_get_history_returns_entries(tmp_path):
    sessions_dir = tmp_path / "sessions"
    session.append("chat1", "user", "one", sessions_dir=sessions_dir)
    session.append("chat1", "assistant", "two", sessions_dir=sessions_dir)
    entries = session.get_history("chat1", sessions_dir=sessions_dir)
    assert len(entries) == 2
    assert entries[0]["content"] == "one"
    assert entries[1]["content"] == "two"


def test_get_history_respects_limit(tmp_path):
    sessions_dir = tmp_path / "sessions"
    for i in range(5):
        session.append("chat1", "user", f"msg-{i}", sessions_dir=sessions_dir)
    entries = session.get_history("chat1", limit=1, sessions_dir=sessions_dir)
    assert len(entries) == 1
    assert entries[0]["content"] == "msg-4"


def test_get_history_missing_session(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    assert session.get_history("nonexistent", sessions_dir=sessions_dir) == []


def test_get_history_none_sessions_dir():
    assert session.get_history("anything") == []
