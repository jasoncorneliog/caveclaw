"""Shared test fixtures for the Caveclaw test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from caveclaw.bus import Attachment, InboundMessage, MessageBus
from caveclaw.config import Config


@pytest.fixture
def config() -> Config:
    """A Config with all defaults."""
    return Config()


@pytest.fixture
def bus() -> MessageBus:
    """A fresh MessageBus instance."""
    return MessageBus()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A temporary agent workspace with SOUL.md pre-created."""
    ws = tmp_path / "agent_workspace"
    ws.mkdir()
    (ws / "sessions").mkdir()
    (ws / "SOUL.md").write_text("# Soul\n\nYou are TestAgent.\n")
    return ws


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """A temporary TEMPLATES_DIR with claw, shadow, and grocer stubs."""
    tpl = tmp_path / "templates"
    for name in ("claw", "shadow", "grocer"):
        agent = tpl / name
        agent.mkdir(parents=True)
        (agent / "SOUL.md").write_text(f"# Soul\n\nYou are {name}.\n")
        (agent / "TOOLS.md").write_text(f"# Tools for {name}\n")
    return tpl


@pytest.fixture
def sample_attachment(tmp_path: Path) -> Attachment:
    """An Attachment pointing to a real temp file."""
    img = tmp_path / "photo.png"
    img.write_bytes(b"\x89PNG fake image data")
    return Attachment(
        path=str(img),
        filename="photo.png",
        content_type="image/png",
        size=len(img.read_bytes()),
    )


@pytest.fixture
def inbound_message() -> InboundMessage:
    """A minimal InboundMessage with defaults."""
    return InboundMessage(
        channel="test",
        sender_id="user1",
        chat_id="session-abc",
        content="Hello agent",
    )
