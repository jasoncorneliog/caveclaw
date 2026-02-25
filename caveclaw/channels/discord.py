"""Discord channel — routes messages through the bus."""

from __future__ import annotations

import asyncio
import time as _time
import uuid
from pathlib import Path

import discord

from caveclaw.agent import agent_loop
from caveclaw.bus import Attachment, InboundMessage, MessageBus, OutboundMessage
from caveclaw.config import AGENTS_DIR, Config, TEMPLATES_DIR, agent_dir
from caveclaw.db import get_state, set_state

MAX_DISCORD_LEN = 2000
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_ATTACHMENT_AGE_SECONDS = 7 * 24 * 3600  # 7 days


def _split_message(text: str) -> list[str]:
    """Split text into chunks that fit within Discord's message limit."""
    if len(text) <= MAX_DISCORD_LEN:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= MAX_DISCORD_LEN:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_DISCORD_LEN)
        if split_at == -1:
            split_at = MAX_DISCORD_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


def _available_agents() -> list[str]:
    """List agent names from bundled templates."""
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(d.name for d in TEMPLATES_DIR.iterdir() if d.is_dir())


def _resolve_agent(channel_id: str, config: Config) -> str:
    """Get agent for a channel: DB override > config routing > default."""
    db_val = get_state(f"channel:{channel_id}")
    if db_val:
        return db_val
    return config.discord_routing.get(channel_id, config.default_agent)


async def _download_attachments(
    discord_attachments: list[discord.Attachment],
    agent_name: str,
    max_size: int,
) -> list[Attachment]:
    """Download valid image attachments to the agent's workspace."""
    results: list[Attachment] = []
    workspace = agent_dir(agent_name)
    attachments_dir = workspace / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    for att in discord_attachments:
        content_type = (att.content_type or "").split(";")[0].strip()
        if content_type not in ALLOWED_IMAGE_TYPES:
            continue
        if att.size > max_size:
            continue

        local_name = f"{uuid.uuid4().hex[:12]}_{att.filename}"
        local_path = attachments_dir / local_name

        try:
            await att.save(local_path)
            results.append(Attachment(
                path=str(local_path),
                filename=att.filename,
                content_type=content_type,
                size=att.size,
            ))
        except Exception as e:
            print(f"Failed to download attachment {att.filename}: {e}")

    return results


def _cleanup_attachments(workspace: Path) -> int:
    """Remove attachments older than MAX_ATTACHMENT_AGE_SECONDS."""
    attachments_dir = workspace / "attachments"
    if not attachments_dir.is_dir():
        return 0
    cutoff = _time.time() - MAX_ATTACHMENT_AGE_SECONDS
    removed = 0
    for f in attachments_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed


async def _keep_typing(channel: discord.abc.Messageable) -> None:
    """Hold a typing indicator until cancelled."""
    try:
        async with channel.typing():
            await asyncio.sleep(3600)  # cancelled externally
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Typing indicator error: {e}")


async def _outbound_sender(
    bus: MessageBus,
    bot: discord.Client,
    typing_tasks: dict[str, asyncio.Task[None]],
) -> None:
    """Consume outbound messages and send them to Discord."""
    while True:
        msg: OutboundMessage = await bus.consume_outbound()
        # Stop typing indicator for this channel
        task = typing_tasks.pop(msg.chat_id, None)
        if task:
            task.cancel()
        channel = bot.get_channel(int(msg.chat_id))
        if channel is None:
            continue
        for chunk in _split_message(msg.content):
            await channel.send(chunk)


async def run_discord(config: Config) -> None:
    """Start the Discord bot and agent loop."""
    # Clean up old attachments at startup
    if AGENTS_DIR.is_dir():
        for d in AGENTS_DIR.iterdir():
            if d.is_dir():
                _cleanup_attachments(d)

    intents = discord.Intents.default()
    intents.message_content = True
    bot = discord.Client(intents=intents)
    bus = MessageBus()
    allow_from = set(config.discord_allow_from) if config.discord_allow_from else None
    agents = _available_agents()

    @bot.event
    async def on_ready() -> None:
        print(f"Discord bot connected as {bot.user}")

    typing_tasks: dict[str, asyncio.Task[None]] = {}

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author == bot.user:
            return
        if message.author.bot:
            return
        if allow_from and str(message.author.id) not in allow_from:
            return

        channel_id = str(message.channel.id)
        content = message.content.strip()

        # Handle !agent command
        if content.startswith("!agent"):
            parts = content.split(maxsplit=1)
            if len(parts) == 1:
                # Show current agent
                current = _resolve_agent(channel_id, config)
                await message.channel.send(
                    f"Current agent: **{current}**\nAvailable: {', '.join(agents)}\n"
                    f"Use `!agent <name>` to switch."
                )
            else:
                name = parts[1].strip()
                if name in agents:
                    set_state(f"channel:{channel_id}", name)
                    await message.channel.send(f"Switched to **{name}**.")
                else:
                    await message.channel.send(
                        f"Unknown agent `{name}`. Available: {', '.join(agents)}"
                    )
            return

        agent_name = _resolve_agent(channel_id, config)

        # Download image attachments to the agent workspace
        attachments: list[Attachment] = []
        if message.attachments:
            attachments = await _download_attachments(
                message.attachments, agent_name, config.max_attachment_bytes,
            )

        # Skip if no text and no usable attachments
        if not content and not attachments:
            return

        # Cancel any existing typing task for this channel before starting a new one
        existing = typing_tasks.pop(channel_id, None)
        if existing:
            existing.cancel()
        # Start continuous typing indicator until the reply is sent
        typing_tasks[channel_id] = asyncio.create_task(
            _keep_typing(message.channel)
        )

        await bus.publish_inbound(
            InboundMessage(
                channel="discord",
                sender_id=str(message.author.id),
                chat_id=channel_id,
                content=content,
                agent_name=agent_name,
                attachments=attachments,
            )
        )

    async with bot:
        await asyncio.gather(
            bot.start(config.discord_token),
            agent_loop(config, bus),
            _outbound_sender(bus, bot, typing_tasks),
        )
