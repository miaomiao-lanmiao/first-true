from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path

import yaml

from .ai.prompts import ProviderConfig, PROVIDER_REGISTRY
from .storage import write_private

CONFIG_DIR = Path(os.environ.get("ECHO_CONFIG_DIR", Path.home() / ".config" / "echo")).expanduser()
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
    config = deepcopy(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            if not isinstance(user_config, dict):
                raise ValueError("Echo configuration must contain a YAML object.")
            _deep_merge(config, user_config)
        except (OSError, yaml.YAMLError) as error:
            raise ValueError("Cannot read Echo configuration.") from error
    if not isinstance(config.get("ai"), dict) or not isinstance(config.get("ui"), dict):
        raise ValueError("Echo ai and ui configuration must contain objects.")
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
    merged = deepcopy(DEFAULT_CONFIG)
    _deep_merge(merged, config)
    env_key = os.environ.get("ECHO_API_KEY")
    if env_key and merged["ai"].get("api_key") == env_key:
        stored = {}
        if CONFIG_FILE.exists():
            loaded = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("ai"), dict):
                stored = loaded["ai"]
        merged["ai"]["api_key"] = stored.get("api_key", "")
    write_private(CONFIG_FILE, yaml.safe_dump(merged, default_flow_style=False, allow_unicode=True))


def redacted_config(config: dict) -> dict:
    def visit(value):
        if isinstance(value, list):
            return [visit(child) for child in value]
        if isinstance(value, dict):
            result = {}
            for key, child in value.items():
                if isinstance(key, str) and any(word in key.lower() for word in ("key", "token", "secret", "password")):
                    result[key] = "[REDACTED]" if child else ""
                else:
                    result[key] = visit(child)
            return result
        return deepcopy(value)

    return visit(config)


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_provider_config(config: dict):
    ai = config.get("ai", {})
    provider_name = ai.get("provider", "openai")
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError("Unknown AI provider.")
    registry = PROVIDER_REGISTRY[provider_name]
    base_url = ai.get("base_url") or registry["base_url"]
    model = ai.get("model") or registry["models"][0]
    if provider_name != DEFAULT_CONFIG["ai"]["provider"]:
        if base_url == DEFAULT_CONFIG["ai"]["base_url"]:
            base_url = registry["base_url"]
        if model == DEFAULT_CONFIG["ai"]["model"]:
            model = registry["models"][0]
    return ProviderConfig(
        name=provider_name,
        api_key=ai.get("api_key", ""),
        base_url=base_url,
        model=model,
        temperature=ai.get("temperature", 0.3),
        max_tokens=ai.get("max_tokens", 4096),
    )
