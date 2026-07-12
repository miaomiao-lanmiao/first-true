from __future__ import annotations

import json
from typing import AsyncGenerator, Optional

import httpx

from .prompts import ProviderConfig


class OpenAIProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self.config.base_url}/chat/completions",
                headers=headers, json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def chat(self, messages: list[dict]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers, json=payload,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content")


class DeepSeekProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self.config.base_url}/chat/completions",
                headers=headers, json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def chat(self, messages: list[dict]) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers, json=payload,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content")


class AnthropicProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        system_msg = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                filtered.append(m)

        payload = {
            "model": self.config.model,
            "messages": filtered,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{self.config.base_url}/messages",
                headers=headers, json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue

    async def chat(self, messages: list[dict]) -> Optional[str]:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        system_msg = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                filtered.append(m)

        payload = {
            "model": self.config.model,
            "messages": filtered,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.config.base_url}/messages",
                headers=headers, json=payload,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            blocks = data.get("content", [])
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


class GeminiProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        gemini_messages = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "model" if m["role"] == "assistant" else "user"
            gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})

        url = f"{self.config.base_url}/models/{self.config.model}:streamGenerateContent?alt=sse&key={self.config.api_key}"
        payload = {"contents": gemini_messages}

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue

    async def chat(self, messages: list[dict]) -> Optional[str]:
        gemini_messages = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "model" if m["role"] == "assistant" else "user"
            gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})

        url = f"{self.config.base_url}/models/{self.config.model}:generateContent?key={self.config.api_key}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json={"contents": gemini_messages})
            if resp.status_code != 200:
                return None
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return None


class OllamaProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        payload = {"model": self.config.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.config.base_url}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def chat(self, messages: list[dict]) -> Optional[str]:
        payload = {"model": self.config.model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.config.base_url}/api/chat", json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("message", {}).get("content", "")


def create_provider(config: ProviderConfig):
    key = config.name.lower()
    if key == "openai":
        return OpenAIProvider(config)
    elif key == "deepseek":
        return DeepSeekProvider(config)
    elif key == "anthropic":
        return AnthropicProvider(config)
    elif key == "gemini":
        return GeminiProvider(config)
    elif key == "ollama":
        return OllamaProvider(config)
    else:
        return OpenAIProvider(config)
