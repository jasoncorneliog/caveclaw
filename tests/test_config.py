"""Tests for config loading and agent provisioning."""

import json

import caveclaw.config as config_mod
from caveclaw.config import AgentConfig, Config


def test_config_defaults():
    c = Config()
    assert c.model == "claude-sonnet-4-6"
    assert c.default_agent == "claw"
    assert c.discord_token is None
    assert c.discord_allow_from == []
    assert c.agents == {}
    assert c.discord_routing == {}
    assert c.max_attachment_bytes == 10 * 1024 * 1024


def test_config_custom_fields():
    c = Config(model="custom-model", default_agent="shadow", max_attachment_bytes=5_000_000)
    assert c.model == "custom-model"
    assert c.default_agent == "shadow"
    assert c.max_attachment_bytes == 5_000_000


def test_agent_dir(monkeypatch, tmp_path):
    agents = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)
    assert config_mod.agent_dir("claw") == agents / "claw"


def test_ensure_agent_from_template(monkeypatch, tmp_path, templates_dir):
    agents = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", templates_dir)

    dest = config_mod._ensure_agent("claw")
    assert dest == agents / "claw"
    assert (dest / "SOUL.md").exists()
    assert (dest / "TOOLS.md").exists()
    assert (dest / "sessions").is_dir()


def test_ensure_agent_no_template_generates_stub(monkeypatch, tmp_path):
    agents = tmp_path / "agents"
    empty_templates = tmp_path / "no_templates"
    empty_templates.mkdir()
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", empty_templates)

    dest = config_mod._ensure_agent("unknown_bot")
    assert "unknown_bot" in (dest / "SOUL.md").read_text()


def test_ensure_agent_idempotent(monkeypatch, tmp_path, templates_dir):
    agents = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", templates_dir)

    config_mod._ensure_agent("claw")
    (agents / "claw" / "SOUL.md").write_text("custom content")
    config_mod._ensure_agent("claw")
    assert (agents / "claw" / "SOUL.md").read_text() == "custom content"


def test_resolve_agent_config_default_model(monkeypatch, tmp_path, templates_dir):
    agents = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", templates_dir)

    c = Config(model="my-model")
    model, workspace = config_mod.resolve_agent_config(c, "claw")
    assert model == "my-model"
    assert workspace == agents / "claw"


def test_resolve_agent_config_agent_model_override(monkeypatch, tmp_path, templates_dir):
    agents = tmp_path / "agents"
    monkeypatch.setattr(config_mod, "AGENTS_DIR", agents)
    monkeypatch.setattr(config_mod, "TEMPLATES_DIR", templates_dir)

    c = Config(
        model="default-model",
        agents={"shadow": AgentConfig(model="special-model")},
    )
    model, _ = config_mod.resolve_agent_config(c, "shadow")
    assert model == "special-model"


def test_load_config_from_file(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"model": "loaded-model", "default_agent": "shadow"}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", cfg_path)

    c = config_mod.load_config()
    assert c.model == "loaded-model"
    assert c.default_agent == "shadow"


def test_load_config_defaults_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "nonexistent.json")
    c = config_mod.load_config()
    assert c.model == "claude-sonnet-4-6"


def test_load_config_discord_token_from_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "nonexistent.json")
    monkeypatch.setenv("DISCORD_TOKEN", "env-token-123")
    c = config_mod.load_config()
    assert c.discord_token == "env-token-123"


def test_load_config_env_overrides_file(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"discord_token": "file-token"}))
    monkeypatch.setattr(config_mod, "CONFIG_PATH", cfg_path)
    monkeypatch.setenv("DISCORD_TOKEN", "env-token-wins")
    c = config_mod.load_config()
    assert c.discord_token == "env-token-wins"
