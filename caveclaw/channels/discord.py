"""Discord channel — routes messages through the bus."""

from __future__ import annotations

import asyncio

import discord

from caveclaw.agent import agent_loop
from caveclaw.bus import InboundMessage, MessageBus, OutboundMessage
from caveclaw.config import Config, TEMPLATES_DIR
from caveclaw.db import get_state, set_state

MAX_DISCORD_LEN = 2000


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


async def _outbound_sender(
    bus: MessageBus,
    bot: discord.Client,
) -> None:
    """Consume outbound messages and send them to Discord."""
    while True:
        msg: OutboundMessage = await bus.consume_outbound()
        channel = bot.get_channel(int(msg.chat_id))
        if channel is None:
            continue
        for chunk in _split_message(msg.content):
            await channel.send(chunk)


async def run_discord(config: Config) -> None:
    """Start the Discord bot and agent loop."""
    intents = discord.Intents.default()
    intents.message_content = True
    bot = discord.Client(intents=intents)
    bus = MessageBus()
    allow_from = set(config.discord_allow_from) if config.discord_allow_from else None
    agents = _available_agents()

    @bot.event
    async def on_ready() -> None:
        print(f"Discord bot connected as {bot.user}")

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
        await message.channel.trigger_typing()

        await bus.publish_inbound(
            InboundMessage(
                channel="discord",
                sender_id=str(message.author.id),
                chat_id=channel_id,
                content=content,
                agent_name=agent_name,
            )
        )

    async with bot:
        await asyncio.gather(
            bot.start(config.discord_token),
            agent_loop(config, bus),
            _outbound_sender(bus, bot),
        )
