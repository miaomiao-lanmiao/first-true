from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 4096


PROVIDER_REGISTRY: dict[str, dict] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "docs": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "docs": "https://platform.deepseek.com/api_keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "docs": "https://console.anthropic.com/",
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "docs": "https://aistudio.google.com/apikey",
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434",
        "models": ["llama3.1", "qwen2.5", "mistral", "codellama"],
        "docs": "https://ollama.com",
    },
}

SYSTEM_PROMPT = """You are Echo, a terminal AI coding assistant.

You help users with:
- Code explanation, review, and debugging
- Code generation and refactoring
- Architecture and design advice
- General programming questions
- File and project analysis

Guidelines:
- Be concise and precise
- Use code blocks with language tags
- When suggesting changes, show the full context
- Think step by step for complex problems
- Keep responses terminal-friendly

You are running in a terminal environment."""

SYSTEM_PROMPTS = {
    "default": SYSTEM_PROMPT,
    "code": """You are Echo, a terminal AI coding assistant.

Focus on code-related tasks: writing, reviewing, debugging, and explaining code.
Be concise. Show code examples. Use code blocks with language tags.""",
    "chat": """You are Echo, a terminal AI assistant. Be helpful, natural, and concise.""",
}
