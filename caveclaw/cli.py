"""CLI entry point — `caveclaw agent` for interactive chat, `caveclaw gateway` for Discord."""

from __future__ import annotations

import asyncio
import uuid

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown

from caveclaw.agent import agent_loop
from caveclaw.bus import InboundMessage, MessageBus
from caveclaw.config import CONFIG_DIR, Config, load_config
from caveclaw.db import init_db

app = typer.Typer(help="Caveclaw — AI agent CLI")
console = Console()


@app.command()
def agent(
    session_id: str = typer.Option(None, help="Session ID to resume"),
    name: str = typer.Option("claw", help="Agent name"),
) -> None:
    """Interactive terminal chat with a named agent."""
    config = load_config()
    init_db()

    chat_id = session_id or str(uuid.uuid4())[:8]
    console.print(f"[dim]Agent: {name} | Session: {chat_id}[/dim]")
    console.print("[dim]Type 'exit' or Ctrl-D to quit.[/dim]\n")

    asyncio.run(_agent_repl(config, chat_id, name))


async def _agent_repl(config: Config, chat_id: str, agent_name: str = "claw") -> None:
    bus = MessageBus()

    agent_task = asyncio.create_task(agent_loop(config, bus))

    history_file = CONFIG_DIR / "prompt_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_session: PromptSession = PromptSession(
        history=FileHistory(str(history_file))
    )

    try:
        while True:
            try:
                user_input = await asyncio.to_thread(
                    prompt_session.prompt, "you> "
                )
            except (EOFError, KeyboardInterrupt):
                break

            text = user_input.strip()
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break

            await bus.publish_inbound(
                InboundMessage(
                    channel="cli",
                    sender_id="user",
                    chat_id=chat_id,
                    content=text,
                    agent_name=agent_name,
                )
            )

            response = await bus.consume_outbound()
            console.print()
            console.print(Markdown(response.content))
            console.print()
    finally:
        agent_task.cancel()


@app.command()
def gateway() -> None:
    """Run the Discord gateway bot."""
    from caveclaw.channels.discord import run_discord

    config = load_config()
    if not config.discord_token:
        console.print("[red]No discord_token set. Add it to ~/.caveclaw/config.json[/red]")
        raise typer.Exit(1)

    init_db()
    asyncio.run(run_discord(config))
