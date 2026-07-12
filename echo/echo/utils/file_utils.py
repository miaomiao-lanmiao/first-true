from __future__ import annotations

from pathlib import Path


def read_file_safe(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def get_project_context(path: str = ".") -> str:
    target = Path(path).resolve()
    if not target.exists():
        return ""
    if target.is_file():
        content = read_file_safe(target)
        return f"File: {target.name}\n\n{content}" if content else ""

    parts = []
    py_files = list(target.rglob("*.py"))[:5]
    for f in py_files:
        content = read_file_safe(f)
        if content:
            rel = f.relative_to(target)
            parts.append(f"--- {rel} ---\n{content[:2000]}")
    return "\n\n".join(parts)
