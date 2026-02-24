"""Long-term memory — MEMORY.md (updateable) and HISTORY.md (append-only)."""

from __future__ import annotations

import time
from pathlib import Path


def _memory_path(workspace: Path) -> Path:
    return workspace / "MEMORY.md"


def _history_path(workspace: Path) -> Path:
    return workspace / "HISTORY.md"


def read_memory(workspace: Path) -> str:
    """Read MEMORY.md, return empty string if it doesn't exist."""
    path = _memory_path(workspace)
    if path.exists():
        return path.read_text()
    return ""


def write_memory(workspace: Path, content: str) -> None:
    """Overwrite MEMORY.md with new content."""
    workspace.mkdir(parents=True, exist_ok=True)
    _memory_path(workspace).write_text(content)


def read_history(workspace: Path) -> str:
    """Read HISTORY.md, return empty string if it doesn't exist."""
    path = _history_path(workspace)
    if path.exists():
        return path.read_text()
    return ""


def append_history(workspace: Path, event: str) -> None:
    """Append an event to HISTORY.md."""
    workspace.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with _history_path(workspace).open("a") as f:
        f.write(f"- [{ts}] {event}\n")
