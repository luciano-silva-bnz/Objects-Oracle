from __future__ import annotations

import json
from typing import Any

from .config import TOKEN_STORAGE_FILE


def save_tokens(data: dict[str, Any]) -> None:
    TOKEN_STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_STORAGE_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def load_tokens() -> dict[str, Any] | None:
    if not TOKEN_STORAGE_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_STORAGE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_refresh_token() -> str | None:
    tokens = load_tokens()
    if not tokens:
        return None
    return tokens.get("refreshToken") or tokens.get("refresh_token")
