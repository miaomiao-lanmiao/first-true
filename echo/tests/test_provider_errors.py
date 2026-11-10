from __future__ import annotations

import json
import traceback
import unittest
from unittest.mock import patch

import httpx

from echo.ai import provider
from echo.ai.prompts import ProviderConfig


PROVIDERS = {
    "openai": provider.OpenAIProvider,
    "deepseek": provider.DeepSeekProvider,
    "anthropic": provider.AnthropicProvider,
    "gemini": provider.GeminiProvider,
    "ollama": provider.OllamaProvider,
}
MESSAGES = [{"role": "user", "content": "synthetic test request"}]
SENSITIVE = "synthetic-provider-private-value"
REAL_ASYNC_CLIENT = httpx.AsyncClient


def make_provider(name):
    return PROVIDERS[name](ProviderConfig(name=name, api_key=SENSITIVE,
                                         base_url="https://provider.example.invalid",
                                         model="synthetic-model"))


def mock_client(handler):
    return patch.object(provider.httpx, "AsyncClient", side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(
        transport=httpx.MockTransport(handler), **kwargs,
    ))


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_http_responses_raise_without_leaking_request_or_response(self):
        for name in PROVIDERS:
            for status in (401, 429, 500):
                for streaming in (True, False):
                    with self.subTest(provider=name, status=status, streaming=streaming):
                        def handler(request):
                            return httpx.Response(status, json={"error": SENSITIVE}, request=request)
                        with mock_client(handler):
                            with self.assertRaises(provider.ProviderError) as failure:
                                instance = make_provider(name)
                                if streaming:
                                    _ = [chunk async for chunk in instance.chat_stream(MESSAGES)]
                                else:
                                    await instance.chat(MESSAGES)
                        self.assertNotIn(SENSITIVE, str(failure.exception))
                        self.assertNotIn("provider.example.invalid", str(failure.exception))
                        self.assertIn(str(status), str(failure.exception))

    async def test_transport_failures_are_sanitized_for_every_provider(self):
        for name in PROVIDERS:
            for streaming in (True, False):
                with self.subTest(provider=name, streaming=streaming):
                    def handler(request):
                        raise httpx.ConnectError(f"Network failure involving {SENSITIVE}", request=request)
                    with mock_client(handler):
                        with self.assertRaises(provider.ProviderError) as failure:
                            instance = make_provider(name)
                            if streaming:
                                _ = [chunk async for chunk in instance.chat_stream(MESSAGES)]
                            else:
                                await instance.chat(MESSAGES)
                    self.assertNotIn(SENSITIVE, str(failure.exception))
                    formatted = "".join(traceback.format_exception(failure.exception))
                    self.assertNotIn(SENSITIVE, formatted)

    async def test_explicit_error_payloads_fail_instead_of_silent_empty_success(self):
        for name in PROVIDERS:
            for streaming in (True, False):
                with self.subTest(provider=name, streaming=streaming):
                    error = {"error": {"message": SENSITIVE}}
                    def handler(request):
                        if not streaming:
                            return httpx.Response(200, json=error, request=request)
                        line = json.dumps(error)
                        body = f"{line}\n" if name == "ollama" else f"data: {line}\n\n"
                        return httpx.Response(200, text=body, request=request)
                    with mock_client(handler):
                        with self.assertRaises(provider.ProviderError) as failure:
                            instance = make_provider(name)
                            if streaming:
                                _ = [chunk async for chunk in instance.chat_stream(MESSAGES)]
                            else:
                                await instance.chat(MESSAGES)
                    self.assertNotIn(SENSITIVE, str(failure.exception))

    async def test_successful_responses_keep_streaming_and_nonstreaming_text(self):
        stream_chunks = {
            "openai": {"choices": [{"delta": {"content": "hello"}}]},
            "deepseek": {"choices": [{"delta": {"content": "hello"}}]},
            "anthropic": {"type": "content_block_delta", "delta": {"text": "hello"}},
            "gemini": {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]},
            "ollama": {"message": {"content": "hello"}, "done": True},
        }
        responses = {
            "openai": {"choices": [{"message": {"content": "hello"}}]},
            "deepseek": {"choices": [{"message": {"content": "hello"}}]},
            "anthropic": {"content": [{"type": "text", "text": "hello"}]},
            "gemini": stream_chunks["gemini"],
            "ollama": stream_chunks["ollama"],
        }
        for name in PROVIDERS:
            for streaming in (True, False):
                with self.subTest(provider=name, streaming=streaming):
                    def handler(request):
                        if not streaming:
                            return httpx.Response(200, json=responses[name], request=request)
                        line = json.dumps(stream_chunks[name])
                        body = f"{line}\n" if name == "ollama" else f"data: {line}\n\n"
                        return httpx.Response(200, text=body, request=request)
                    with mock_client(handler):
                        instance = make_provider(name)
                        if streaming:
                            self.assertEqual([chunk async for chunk in instance.chat_stream(MESSAGES)], ["hello"])
                        else:
                            self.assertEqual(await instance.chat(MESSAGES), "hello")

    async def test_transport_failure_after_a_partial_token_is_sanitized(self):
        chunks = {
            "openai": {"choices": [{"delta": {"content": "hello"}}]},
            "deepseek": {"choices": [{"delta": {"content": "hello"}}]},
            "anthropic": {"type": "content_block_delta", "delta": {"text": "hello"}},
            "gemini": {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]},
            "ollama": {"message": {"content": "hello"}, "done": False},
        }
        for name in PROVIDERS:
            with self.subTest(provider=name):
                class BrokenStream(httpx.AsyncByteStream):
                    async def __aiter__(self):
                        body = json.dumps(chunks[name])
                        yield (f"{body}\n" if name == "ollama" else f"data: {body}\n\n").encode()
                        raise httpx.ReadError(SENSITIVE)
                def handler(request):
                    return httpx.Response(200, stream=BrokenStream(), request=request)
                seen = []
                with mock_client(handler):
                    with self.assertRaises(provider.ProviderError) as failure:
                        async for chunk in make_provider(name).chat_stream(MESSAGES):
                            seen.append(chunk)
                self.assertEqual(seen, ["hello"])
                self.assertNotIn(SENSITIVE, str(failure.exception))
                self.assertNotIn(SENSITIVE, "".join(traceback.format_exception(failure.exception)))


if __name__ == "__main__":
    unittest.main()
