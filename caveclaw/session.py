"""JSONL conversation history — one file per conversation."""

from __future__ import annotations

import json
import time
from pathlib import Path


def _session_path(key: str, sessions_dir: Path) -> Path:
    return sessions_dir / f"{key}.jsonl"


def get_or_create(key: str, sessions_dir: Path) -> Path:
    """Return the session file path, creating it if needed."""
    path = _session_path(key, sessions_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


def append(
    key: str,
    role: str,
    content: str,
    sessions_dir: Path,
    attachments: list[dict] | None = None,
) -> None:
    """Append a message to the session log."""
    path = get_or_create(key, sessions_dir)
    entry: dict = {"ts": time.time(), "role": role, "content": content}
    if attachments:
        entry["attachments"] = attachments
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def get_history(key: str, limit: int = 100, sessions_dir: Path | None = None) -> list[dict]:
    """Return the last `limit` messages from a session."""
    if sessions_dir is None:
        return []
    path = _session_path(key, sessions_dir)
    if not path.exists():
        return []
    lines = path.read_text().strip().splitlines()
    entries = [json.loads(line) for line in lines[-limit:]]
    return entries
