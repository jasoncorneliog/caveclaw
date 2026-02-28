# Caveclaw

An AI agent that lives in your cave and gets things done through chat.

Built on [Anthropic's Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Supports multiple named agents with isolated personalities, memory, and sessions. CLI and Discord channels.

## Architecture

```
┌─────────┐   ┌─────────────┐
│   CLI   │   │   Discord   │
│  (typer)│   │ (discord.py)│
└────┬────┘   └──────┬──────┘
     │               │
     │  InboundMsg   │  InboundMsg
     │  + agent_name │  + agent_name (from discord_routing)
     ▼               ▼
┌────────────────────────────┐
│         MessageBus         │
│  inbound queue → outbound  │
└─────────────┬──────────────┘
              │
              ▼
┌─────────────────────────────┐
│        Agent Loop           │
│  consume → resolve agent    │
│  → create_task(handle_msg)  │
└─────────────┬───────────────┘
              │
    ┌─────────┴──────────┐
    ▼                    ▼
┌────────┐          ┌────────┐
│  claw  │          │ shadow │
│ agent  │          │ agent  │
├────────┤          ├────────┤
│SOUL.md │          │SOUL.md │
│MEMORY  │          │MEMORY  │
│sessions│          │sessions│
└───┬────┘          └───┬────┘
    │                   │
    ▼                   ▼
┌─────────────────────────────┐
│     Claude Agent SDK        │
│  ClaudeSDKClient + tools    │
│  (Bash, Read, Write, Web)   │
└─────────────────────────────┘
```

## Quick Start

```bash
pip install -e .
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...  # from `claude setup-token`
caveclaw agent
```

No onboarding needed. Agents are defined in `agents/` and auto-provisioned on first run.

## Docker

```bash
docker build -t caveclaw .

# Interactive chat
docker run -it -e CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-... \
  -v ~/.caveclaw:/home/caveclaw/.caveclaw caveclaw agent

# Discord bot
docker run -d --restart unless-stopped \
  -e CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-... \
  -v ~/.caveclaw:/home/caveclaw/.caveclaw caveclaw gateway
```

## CI/CD

GitHub Actions pipeline with a self-hosted runner:

- **PR Check** (`pr-check.yml`): Runs tests on every pull request to `main`
- **CI/CD** (`ci-cd.yml`): On push to `main` — runs tests, builds Docker image, pushes to GHCR (`ghcr.io/jasoncorneliog/caveclaw`)
- **Deploy** (`deploy.yml`): Manual trigger — pulls latest image and deploys via `docker compose`

### Production Deployment

```bash
# On the server, secrets live in a single .env file
cat ~/.caveclaw/.env
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
DISCORD_TOKEN=MTIz...

# Deploy manually (or trigger via GitHub Actions UI)
docker compose -f docker-compose.prod.yml up -d
```

### Self-Hosted Runner Setup

1. Install Docker + `docker-compose-plugin` on your Ubuntu server
2. Create a runner user: `sudo useradd -m -s /bin/bash github-runner && sudo usermod -aG docker github-runner`
3. Install the GitHub Actions runner: repo **Settings > Actions > Runners > New self-hosted runner**, install as a systemd service
4. Create the secrets file:
   ```bash
   mkdir -p ~/.caveclaw
   cat > ~/.caveclaw/.env << 'EOF'
   CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
   DISCORD_TOKEN=MTIz...
   EOF
   chmod 600 ~/.caveclaw/.env
   ```
5. Optionally create `~/.caveclaw/config.json` for non-secret settings (`discord_allow_from`, `default_agent`, etc.)

## Agents

Agents are defined declaratively in `agents/`:

```
agents/
├── claw/                # primary agent
│   ├── SOUL.md          # personality
│   └── TOOLS.md         # tool guidelines
└── shadow/              # research & recon agent
    ├── SOUL.md
    └── TOOLS.md
```

On first use, templates are copied to `~/.caveclaw/agents/<name>/` where runtime data (memory, sessions) accumulates.

```bash
caveclaw agent                # chat with claw (default)
caveclaw agent --name shadow  # chat with shadow
```

To add a new agent, create a directory in `agents/` with a `SOUL.md`.

### Discord Routing

Switch agents per channel directly from Discord:

```
!agent          # show current agent + available agents
!agent shadow   # switch this channel to shadow
```

The mapping is persisted in SQLite so it survives restarts.

You can also set default routing in `~/.caveclaw/config.json`:

```json
{
  "default_agent": "claw",
  "discord_routing": {
    "CHANNEL_ID": "shadow"
  }
}
```

Resolution order: `!agent` override → `discord_routing` config → `default_agent`.

## Discord Setup

1. Create app at [Discord Developer Portal](https://discord.com/developers/applications)
2. **Bot** tab: enable **Message Content Intent**, disable **Public Bot** (enable only if needed for Guild Install)
3. **OAuth2 → URL Generator**: scope `bot`, permissions: `View Channels`, `Send Messages`, `Read Message History`
4. Open the generated URL to invite bot to your server
5. Use private channels — add the bot explicitly to each channel
6. Get your Discord user ID (right-click → Copy User ID with Developer Mode on)

## Config

Optional. Stored at `~/.caveclaw/config.json`. If absent, defaults are used.

```json
{
  "model": "claude-sonnet-4-6",
  "discord_token": "YOUR_BOT_TOKEN",
  "discord_allow_from": ["YOUR_DISCORD_USER_ID"],
  "default_agent": "claw",
  "agents": {
    "claw": {},
    "shadow": { "model": "claude-opus-4-6" }
  },
  "discord_routing": {}
}
```

- **`discord_token`**: Bot token from Developer Portal (never commit to git). Can also be set via `DISCORD_TOKEN` environment variable, which takes precedence over the config file.
- **`discord_allow_from`**: Whitelist of numeric Discord user IDs. Only these users can interact with the bot. **Always set this.**
- **`discord_routing`**: Optional static channel→agent mapping (overridden by `!agent` command)

## License

MIT
