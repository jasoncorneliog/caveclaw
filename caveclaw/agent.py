"""Thin wrapper around claude-agent-sdk."""

from __future__ import annotations

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from caveclaw import memory as mem
from caveclaw.bus import InboundMessage, MessageBus, OutboundMessage
from caveclaw.config import Config, resolve_agent_config
from caveclaw import session


def _build_system_prompt(workspace: Path) -> str:
    """Combine SOUL.md + MEMORY.md into a system prompt."""
    parts: list[str] = []

    soul_path = workspace / "SOUL.md"
    if soul_path.exists():
        parts.append(soul_path.read_text().strip())

    memory_text = mem.read_memory(workspace)
    if memory_text:
        parts.append(f"## Memory\n\n{memory_text.strip()}")

    return "\n\n".join(parts) if parts else ""


def _extract_text(message: AssistantMessage) -> str:
    """Pull text content out of an AssistantMessage."""
    texts = []
    for block in message.content:
        if isinstance(block, TextBlock):
            texts.append(block.text)
    return "\n".join(texts)


async def handle_message(
    message: InboundMessage,
    config: Config,
    bus: MessageBus,
) -> None:
    """Process one inbound message through the appropriate agent."""
    model, workspace = resolve_agent_config(config, message.agent_name)
    sessions_dir = workspace / "sessions"
    system_prompt = _build_system_prompt(workspace)

    # Load conversation history before appending the new message
    history = session.get_history(message.chat_id, limit=50, sessions_dir=sessions_dir)
    if history:
        lines = [f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}" for h in history]
        system_prompt += "\n\n## Conversation History\n\n" + "\n\n".join(lines)

    # Persist the user message
    session.append(message.chat_id, "user", message.content, sessions_dir=sessions_dir)

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(workspace),
        model=model,
        permission_mode="bypassPermissions",
    )

    result_text = ""

    async with ClaudeSDKClient(options=options) as client:
        await client.query(message.content)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                text = _extract_text(msg)
                if text:
                    result_text = text
            elif isinstance(msg, ResultMessage):
                if hasattr(msg, "text") and msg.text:
                    result_text = msg.text

    if not result_text:
        result_text = "(no response)"

    # Persist the assistant message
    session.append(message.chat_id, "assistant", result_text, sessions_dir=sessions_dir)

    # Log to HISTORY.md
    mem.append_history(workspace, f"Responded to {message.sender_id} in {message.channel}")

    await bus.publish_outbound(
        OutboundMessage(
            channel=message.channel,
            chat_id=message.chat_id,
            content=result_text,
        )
    )


async def _safe_handle(
    message: InboundMessage, config: Config, bus: MessageBus
) -> None:
    try:
        await handle_message(message, config, bus)
    except Exception as e:
        await bus.publish_outbound(
            OutboundMessage(
                channel=message.channel,
                chat_id=message.chat_id,
                content=f"Error: {e}",
            )
        )


async def agent_loop(config: Config, bus: MessageBus) -> None:
    """Main loop: consume inbound messages and dispatch concurrently."""
    while True:
        message = await bus.consume_inbound()
        asyncio.create_task(_safe_handle(message, config, bus))
