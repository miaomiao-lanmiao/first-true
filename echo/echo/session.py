from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

SESSION_DIR = Path.home() / ".config" / "echo" / "sessions"


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


def save_session(session: Session) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in session.title)
    path = SESSION_DIR / f"{safe}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)


def load_session(title: str) -> Optional[Session]:
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
    path = SESSION_DIR / f"{safe}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return Session.from_dict(data)


def list_sessions() -> list[str]:
    if not SESSION_DIR.exists():
        return []
    return sorted([p.stem for p in SESSION_DIR.glob("*.json")], reverse=True)
