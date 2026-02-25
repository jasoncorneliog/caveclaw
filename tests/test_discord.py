"""Tests for Discord channel utilities."""

import os
import time

import pytest
from unittest.mock import AsyncMock, MagicMock

import caveclaw.channels.discord as discord_mod
import caveclaw.config as config_mod
import caveclaw.db as db_mod
from caveclaw.config import Config


# --- _split_message ---


def test_split_message_short():
    assert discord_mod._split_message("hello") == ["hello"]


def test_split_message_exact_limit():
    text = "x" * 2000
    assert discord_mod._split_message(text) == [text]


def test_split_message_splits_on_newline():
    line = "a" * 1000
    text = f"{line}\n{line}\n{line}"
    chunks = discord_mod._split_message(text)
    assert len(chunks) >= 2
    assert all(len(c) <= 2000 for c in chunks)


def test_split_message_no_newline():
    text = "x" * 4500
    chunks = discord_mod._split_message(text)
    assert len(chunks) == 3
    assert chunks[0] == "x" * 2000
    assert chunks[1] == "x" * 2000
    assert chunks[2] == "x" * 500


# --- _available_agents ---


def test_available_agents(monkeypatch, templates_dir):
    monkeypatch.setattr(discord_mod, "TEMPLATES_DIR", templates_dir)
    agents = discord_mod._available_agents()
    assert agents == ["claw", "grocer", "shadow"]


def test_available_agents_missing_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(discord_mod, "TEMPLATES_DIR", tmp_path / "nope")
    assert discord_mod._available_agents() == []


# --- _resolve_agent ---


def test_resolve_agent_db_override(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    db_mod.init_db()
    db_mod.set_state("channel:123", "shadow")
    assert discord_mod._resolve_agent("123", Config()) == "shadow"


def test_resolve_agent_routing_config(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    db_mod.init_db()
    assert discord_mod._resolve_agent("456", Config(discord_routing={"456": "grocer"})) == "grocer"


def test_resolve_agent_default(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    db_mod.init_db()
    assert discord_mod._resolve_agent("789", Config(default_agent="claw")) == "claw"


# --- _cleanup_attachments ---


def test_cleanup_attachments_removes_old(tmp_path):
    att_dir = tmp_path / "attachments"
    att_dir.mkdir()
    old_file = att_dir / "old.png"
    old_file.write_bytes(b"data")
    old_ts = time.time() - (10 * 24 * 3600)
    os.utime(old_file, (old_ts, old_ts))

    removed = discord_mod._cleanup_attachments(tmp_path)
    assert removed == 1
    assert not old_file.exists()


def test_cleanup_attachments_keeps_recent(tmp_path):
    att_dir = tmp_path / "attachments"
    att_dir.mkdir()
    new_file = att_dir / "new.png"
    new_file.write_bytes(b"data")

    removed = discord_mod._cleanup_attachments(tmp_path)
    assert removed == 0
    assert new_file.exists()


def test_cleanup_attachments_no_dir(tmp_path):
    assert discord_mod._cleanup_attachments(tmp_path) == 0


# --- _download_attachments ---


async def test_download_attachments_filters_non_images(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "AGENTS_DIR", tmp_path / "agents")

    mock_att = MagicMock()
    mock_att.content_type = "application/pdf"
    mock_att.size = 100
    mock_att.filename = "doc.pdf"

    result = await discord_mod._download_attachments([mock_att], "claw", 10_000_000)
    assert result == []


async def test_download_attachments_filters_oversize(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "AGENTS_DIR", tmp_path / "agents")

    mock_att = MagicMock()
    mock_att.content_type = "image/png"
    mock_att.size = 20_000_000
    mock_att.filename = "huge.png"

    result = await discord_mod._download_attachments([mock_att], "claw", 10_000_000)
    assert result == []


async def test_download_attachments_saves_valid_image(monkeypatch, tmp_path):
    agents = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)

    mock_att = AsyncMock()
    mock_att.content_type = "image/png"
    mock_att.size = 1024
    mock_att.filename = "photo.png"
    mock_att.save = AsyncMock()

    result = await discord_mod._download_attachments([mock_att], "claw", 10_000_000)
    assert len(result) == 1
    assert result[0].filename == "photo.png"
    assert result[0].content_type == "image/png"
    mock_att.save.assert_called_once()
