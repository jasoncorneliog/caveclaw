"""Load settings from ~/.caveclaw/config.json."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

CONFIG_DIR = Path.home() / ".caveclaw"
CONFIG_PATH = CONFIG_DIR / "config.json"
AGENTS_DIR = CONFIG_DIR / "agents"

# Bundled agent templates — repo root for local dev, /app/agents for Docker
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = _PACKAGE_ROOT / "agents"
if not TEMPLATES_DIR.is_dir():
    TEMPLATES_DIR = Path("/app/agents")


class AgentConfig(BaseModel):
    model: str | None = None


class Config(BaseModel):
    model: str = "claude-sonnet-4-6"
    discord_token: str | None = None
    discord_allow_from: list[str] = Field(default_factory=list)
    default_agent: str = "claw"
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    discord_routing: dict[str, str] = Field(default_factory=dict)
    max_attachment_bytes: int = 10 * 1024 * 1024  # 10 MB


def agent_dir(name: str) -> Path:
    """Return ~/.caveclaw/agents/<name>/."""
    return AGENTS_DIR / name


def _ensure_agent(name: str) -> Path:
    """Auto-provision agent dir from bundled template if it doesn't exist."""
    dest = agent_dir(name)
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "sessions").mkdir(exist_ok=True)
        template = TEMPLATES_DIR / name
        if template.is_dir():
            for src_file in template.iterdir():
                shutil.copy2(str(src_file), str(dest / src_file.name))
        else:
            (dest / "SOUL.md").write_text(f"# Soul\n\nYou are {name}, an AI assistant.\n")
    return dest


def resolve_agent_config(config: Config, name: str) -> tuple[str, Path]:
    """Return (model, workspace_path) for a named agent. Auto-provisions if needed."""
    agent_cfg = config.agents.get(name)
    model = agent_cfg.model if agent_cfg and agent_cfg.model else config.model
    workspace = _ensure_agent(name)
    return model, workspace


def load_config() -> Config:
    """Load config from disk, or return defaults.

    Environment variables override config file values:
      - DISCORD_TOKEN overrides discord_token
    """
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        config = Config(**data)
    else:
        config = Config()
    discord_token = os.environ.get("DISCORD_TOKEN")
    if discord_token:
        config.discord_token = discord_token
    return config
