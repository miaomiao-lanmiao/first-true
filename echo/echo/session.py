from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import CONFIG_DIR
from .storage import safe_child, write_private

SESSION_DIR = CONFIG_DIR / "sessions"


class Session:
    def __init__(self, title: str = "default"):
        self.title = title
        self.messages: list[dict] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data: dict):
        session = cls(data.get("title", "default"))
        session.created_at = data.get("created_at", session.created_at)
        session.updated_at = data.get("updated_at", session.updated_at)
        session.messages = data.get("messages", [])
        return session


def _title_path(title: str) -> Path:
    legacy = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:100]
    if not legacy.strip():
        legacy = "default"
    path = safe_child(SESSION_DIR, legacy, ".json", allow_spaces=True)
    previous = safe_child(SESSION_DIR, legacy.replace(" ", "_"), ".json")
    return previous if not path.exists() and previous.exists() else path


def read_session(path: Path) -> dict:
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError()
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
            raise ValueError()
        for message in data["messages"]:
            if not isinstance(message, dict) or not all(isinstance(message.get(key), str) for key in ("role", "content")):
                raise ValueError()
        if "title" in data and not isinstance(data["title"], str):
            raise ValueError()
        for key in ("created_at", "updated_at"):
            if key in data and not isinstance(data[key], str):
                raise ValueError()
        return data
    except (OSError, ValueError, UnicodeError):
        raise ValueError("Stored session data is invalid.") from None


def save_session(session: Session) -> None:
    path = _title_path(session.title)
    write_private(path, json.dumps(session.to_dict(), indent=2, ensure_ascii=False))


def load_session(title: str) -> Optional[Session]:
    path = _title_path(title)
    if not path.exists():
        return None
    return Session.from_dict(read_session(path))


def list_sessions() -> list[str]:
    if not SESSION_DIR.exists():
        return []
    return sorted([p.stem for p in SESSION_DIR.glob("*.json")], reverse=True)
