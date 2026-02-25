"""Tests for agent logic and SDK interaction."""

from unittest.mock import AsyncMock, MagicMock

import caveclaw.config as config_mod
from caveclaw.agent import _build_attachment_prompt, _build_system_prompt, _extract_text, handle_message
from caveclaw.bus import InboundMessage, MessageBus
from caveclaw.config import Config


# --- Pure logic tests ---


def test_build_system_prompt_with_soul(workspace):
    prompt = _build_system_prompt(workspace)
    assert "TestAgent" in prompt


def test_build_system_prompt_with_memory(workspace):
    (workspace / "MEMORY.md").write_text("Remember: user likes coffee")
    prompt = _build_system_prompt(workspace)
    assert "## Memory" in prompt
    assert "user likes coffee" in prompt


def test_build_system_prompt_empty_workspace(tmp_path):
    assert _build_system_prompt(tmp_path) == ""


def test_build_attachment_prompt_empty():
    assert _build_attachment_prompt([]) == ""


def test_build_attachment_prompt_with_files(sample_attachment):
    prompt = _build_attachment_prompt([sample_attachment])
    assert "photo.png" in prompt
    assert "image/png" in prompt
    assert "Read tool" in prompt


def test_extract_text_from_assistant_message():
    block = MagicMock()
    block.text = "Hello world"
    msg = MagicMock()
    msg.content = [block]
    # Make isinstance(block, TextBlock) work by using type(block)
    import caveclaw.agent as agent_mod
    original = agent_mod.TextBlock
    try:
        agent_mod.TextBlock = type(block)
        result = _extract_text(msg)
    finally:
        agent_mod.TextBlock = original
    assert result == "Hello world"


def test_extract_text_skips_non_text_blocks():
    text_block = MagicMock()
    text_block.text = "real text"
    other_block = MagicMock(spec=[])

    msg = MagicMock()
    msg.content = [other_block, text_block]
    import caveclaw.agent as agent_mod
    original = agent_mod.TextBlock
    try:
        agent_mod.TextBlock = type(text_block)
        result = _extract_text(msg)
    finally:
        agent_mod.TextBlock = original
    assert result == "real text"


# --- handle_message tests ---


async def _async_iter(items):
    for item in items:
        yield item


async def test_handle_message_publishes_response(monkeypatch, tmp_path, templates_dir):
    agents_dir = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents_dir)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", templates_dir)

    cfg = Config()
    bus = MessageBus()

    mock_text_block = MagicMock()
    mock_text_block.text = "I am the response"
    mock_assistant_msg = MagicMock()
    mock_assistant_msg.content = [mock_text_block]

    import caveclaw.agent as agent_mod
    monkeypatch.setattr(agent_mod, "TextBlock", type(mock_text_block))
    monkeypatch.setattr(agent_mod, "AssistantMessage", type(mock_assistant_msg))

    mock_client = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = MagicMock(return_value=_async_iter([mock_assistant_msg]))

    mock_client_class = MagicMock()
    mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(agent_mod, "ClaudeSDKClient", mock_client_class)

    msg = InboundMessage(channel="test", sender_id="u", chat_id="s1", content="hi", agent_name="claw")
    await handle_message(msg, cfg, bus)

    out = await bus.consume_outbound()
    assert out.content == "I am the response"
    assert out.channel == "test"
    assert out.chat_id == "s1"


async def test_handle_message_no_response_fallback(monkeypatch, tmp_path, templates_dir):
    agents_dir = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents_dir)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", templates_dir)

    cfg = Config()
    bus = MessageBus()

    mock_client = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = MagicMock(return_value=_async_iter([]))

    mock_client_class = MagicMock()
    mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

    import caveclaw.agent as agent_mod
    monkeypatch.setattr(agent_mod, "ClaudeSDKClient", mock_client_class)

    msg = InboundMessage(channel="test", sender_id="u", chat_id="s2", content="hi", agent_name="claw")
    await handle_message(msg, cfg, bus)

    out = await bus.consume_outbound()
    assert out.content == "(no response)"
