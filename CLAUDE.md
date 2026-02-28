# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Caveclaw — an AI agent that lives in your cave and gets things done through chat. Uses Anthropic's Agent SDK with OAuth. Licensed under MIT.

## Architecture

Multi-agent system with CLI and Discord channels. Single message bus, single agent loop, routing by `agent_name` field on messages. Agents are defined declaratively in code — no onboarding step required.

### Directory Structure

```
caveclaw/                    # repo root
├── pyproject.toml           # Python >= 3.13, deps pinned to latest
├── Dockerfile               # python:3.14-slim + Node 22, non-root user
├── docker-compose.prod.yml  # production deploy (caveclaw gateway)
├── .github/workflows/       # CI/CD pipelines
│   ├── ci-cd.yml            # test + build on push to main
│   ├── deploy.yml           # manual deploy (workflow_dispatch)
│   └── pr-check.yml         # test on PRs
├── agents/                  # declarative agent templates (auto-provisioned at runtime)
│   ├── claw/
│   │   ├── SOUL.md          # primary agent personality
│   │   └── TOOLS.md         # tool guidelines
│   └── shadow/
│       ├── SOUL.md          # research/recon agent personality
│       └── TOOLS.md
└── caveclaw/                # python package
    ├── __init__.py
    ├── config.py            # Pydantic config, agent resolution, auto-provisioning
    ├── bus.py               # InboundMessage/OutboundMessage + async MessageBus
    ├── session.py           # JSONL conversation history per agent
    ├── memory.py            # MEMORY.md (updateable) + HISTORY.md (append-only)
    ├── db.py                # SQLite for scheduled tasks + key-value state
    ├── agent.py             # Claude Agent SDK wrapper, concurrent dispatch
    ├── cli.py               # Typer CLI: agent, gateway
    └── channels/
        └── discord.py       # Discord bot with channel->agent routing
```

### Runtime Storage (~/.caveclaw/)

Auto-created on first run. No onboarding needed.

```
~/.caveclaw/
├── .env                     # secrets: CLAUDE_CODE_OAUTH_TOKEN, DISCORD_TOKEN
├── config.json              # optional — overrides for model, discord, routing
├── caveclaw.db              # shared SQLite
└── agents/
    ├── claw/                # auto-provisioned from repo agents/claw/
    │   ├── SOUL.md
    │   ├── TOOLS.md
    │   ├── MEMORY.md        # created at runtime
    │   ├── HISTORY.md       # created at runtime
    │   └── sessions/
    └── shadow/              # auto-provisioned from repo agents/shadow/
        └── ...
```

### Key Patterns

- **Agents defined in code:** Agent templates live in `agents/` at repo root. `_ensure_agent()` in config.py auto-provisions `~/.caveclaw/agents/<name>/` from bundled templates on first use. No onboarding step.
- **Agent resolution:** `resolve_agent_config(config, name)` returns `(model, workspace_path)`, auto-provisioning the agent dir if needed.
- **Message routing:** `InboundMessage.agent_name` field routes to the correct agent. CLI uses `--name` flag. Discord resolves agent per channel via: DB state (`channel:<id>` key, set by `!agent` command) → `config.discord_routing` → `config.default_agent`. Default agent is `claw`.
- **Concurrent dispatch:** `agent_loop` uses `asyncio.create_task()` so messages for different agents run concurrently.
- **Session isolation:** Each agent stores sessions in its own `agents/<name>/sessions/` directory.
- **Memory isolation:** `memory.py` takes `workspace: Path` — each agent gets its own MEMORY.md and HISTORY.md.
- **Auth:** `CLAUDE_CODE_OAUTH_TOKEN` env var (from `claude setup-token`). Never stored in config.
- **Env var overrides:** `DISCORD_TOKEN` env var overrides `discord_token` in config.json. Allows centralizing all secrets in `~/.caveclaw/.env`.
- **`CAVECLAW_DIR` env var:** Overrides the default `~/.caveclaw` data directory. Used in Docker to point the app at `/data` (the volume mount target), avoiding home directory permission issues. Falls back to `~/.caveclaw` when unset.

### Claude Agent SDK Usage

- Import from `claude_agent_sdk`: `ClaudeSDKClient`, `ClaudeAgentOptions`, `AssistantMessage`, `TextBlock`, `ResultMessage`
- Use `ClaudeSDKClient` (not `query()`) for conversation support
- `permission_mode="bypassPermissions"` for autonomous operation
- SDK bundles its own CLI — needs Node.js 18+ at runtime

## Commands

```bash
caveclaw agent [--name claw]     # interactive CLI chat (default: claw)
caveclaw agent --name shadow     # chat with shadow agent
caveclaw gateway                 # run Discord bot
```

### Discord Commands

- `!agent` — show current agent and available agents for the channel
- `!agent <name>` — switch the channel to a different agent (persisted in SQLite)

## Docker

```bash
docker build -t caveclaw .
docker run -it -e CLAUDE_CODE_OAUTH_TOKEN=... -e CAVECLAW_DIR=/data \
  -v ~/.caveclaw:/data caveclaw agent
```

### Production Deployment

```bash
# Deploy using docker compose (reads secrets from ~/.caveclaw/.env)
# UID/GID must be exported so the container runs as the host user
export DOCKER_UID=$(id -u) DOCKER_GID=$(id -g)
docker compose -f docker-compose.prod.yml up -d

# View logs
docker logs caveclaw-gateway --tail=100 -f

# Manual deploy via GitHub Actions UI: Actions → Deploy → Run workflow
```

## CI/CD

Three GitHub Actions workflows, all on a self-hosted runner:

- **`ci-cd.yml`** — push to `main`: test → build Docker image → push to GHCR
- **`deploy.yml`** — manual `workflow_dispatch`: pull image → `docker compose up` → health check
- **`pr-check.yml`** — pull requests to `main`: run tests

Images are pushed to `ghcr.io/jasoncorneliog/caveclaw` tagged with commit SHA and `latest`. GHCR auth uses the automatic `GITHUB_TOKEN`.

## Lessons Learned

When a mistake is made during development, add a concise entry here so it is not repeated.

- **Agents are defined in code, not via onboarding:** Agent templates live in `agents/` at repo root and are auto-provisioned to `~/.caveclaw/agents/` on first use. Never require an onboarding step to create agents.
- **Config paths must be portable:** Never write fully resolved absolute paths into config files. Store with `~`, resolve with `expanduser()` at load time.
- **Claude Agent SDK `permission_mode` values:** Valid values are `acceptEdits`, `bypassPermissions`, `default`, `dontAsk`, `plan`. There is no `auto` mode.
- **`bypassPermissions` cannot run as root:** The Agent SDK refuses `--dangerously-skip-permissions` as root. Always use a non-root user in Docker (`useradd -m caveclaw` + `USER caveclaw`).
- **Docker volume mounts use `/data`, not home directory:** Mount `~/.caveclaw` to `/data` and set `CAVECLAW_DIR=/data`. Don't mount to `/home/caveclaw/.caveclaw` — causes permission issues when the container UID differs from the image's `caveclaw` user.
- **Docker UID override:** `docker-compose.prod.yml` uses `user: "${DOCKER_UID}:${DOCKER_GID}"` so the container process matches the host user's UID. Export these before running `docker compose`. Note: `UID` is a readonly bash variable — use `DOCKER_UID` instead.
- **`pyproject.toml` `readme` field requires the file in Docker context:** `COPY` must include `README.md` or pip fails with "Readme file does not exist".
- **`python:3.14-slim` (Trixie) apt issue:** `docker-clean` config breaks `apt-get update` on Docker Engine < 29. Use Docker 29+ or `python:3.13-slim-bookworm`.
- **Nanobot is not a Claude Agent SDK project:** It has its own agent loop. Don't reference it for SDK patterns.
- **`TEMPLATES_DIR` must work after pip install:** After `pip install`, `Path(__file__).parent.parent` resolves to `site-packages/`, not the repo root. Use a fallback to `/app/agents/` for Docker environments.
- **Discord privileged intents:** The bot requires **Message Content Intent** enabled in the Developer Portal under Bot → Privileged Gateway Intents. Without it, `PrivilegedIntentsRequired` is raised.
- **Discord `discord_allow_from` uses user IDs, not usernames:** Values must be numeric Discord user IDs (e.g. `"123456789012345678"`), obtained via right-click → Copy User ID with Developer Mode enabled.
- **`DISCORD_TOKEN` env var overrides `config.json`:** `load_config()` checks `os.environ.get("DISCORD_TOKEN")` after loading from file. This allows centralizing all secrets in `~/.caveclaw/.env` for production deployments.
