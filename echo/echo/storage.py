from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile


def safe_child(root: Path, identifier: str, suffix: str = "") -> Path:
    if not isinstance(identifier, str) or not re.fullmatch(r"[\w-]{1,100}", identifier):
        raise ValueError("Invalid storage identifier.")
    candidate = root / f"{identifier}{suffix}"
    if candidate.is_symlink() or candidate.resolve().parent != root.resolve():
        raise ValueError("Storage path must remain inside its data directory.")
    return candidate


def write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".echo-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
