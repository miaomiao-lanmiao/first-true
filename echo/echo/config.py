from __future__ import annotations

import os
from pathlib import Path

import yaml

from .ai.prompts import ProviderConfig, PROVIDER_REGISTRY

CONFIG_DIR = Path.home() / ".config" / "echo"
CONFIG_FILE = CONFIG_DIR / "config.yml"

DEFAULT_CONFIG = {
    "ai": {
        "provider": "openai",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "ui": {
        "theme": "catppuccin-mocha",
        "show_token_count": True,
    },
}


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            _deep_merge(config, user_config)
        except Exception:
            pass
    env_key = os.environ.get("ECHO_API_KEY")
    if env_key:
        config["ai"]["api_key"] = env_key
    env_url = os.environ.get("ECHO_BASE_URL")
    if env_url:
        config["ai"]["base_url"] = env_url
    env_model = os.environ.get("ECHO_MODEL")
    if env_model:
        config["ai"]["model"] = env_model
    return config


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_CONFIG)
    _deep_merge(merged, config)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, default_flow_style=False, allow_unicode=True)


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_provider_config(config: dict):
    ai = config.get("ai", {})
    provider_name = ai.get("provider", "openai")
    registry = PROVIDER_REGISTRY.get(provider_name, PROVIDER_REGISTRY["openai"])
    return ProviderConfig(
        name=provider_name,
        api_key=ai.get("api_key", ""),
        base_url=ai.get("base_url", registry["base_url"]),
        model=ai.get("model", registry["models"][0]),
        temperature=ai.get("temperature", 0.3),
        max_tokens=ai.get("max_tokens", 4096),
    )
