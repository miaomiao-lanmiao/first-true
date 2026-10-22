from __future__ import annotations

import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

# Baseline code creates directories at import; sandbox that behavior too.
_import_storage = tempfile.TemporaryDirectory(prefix="echo-import-tests-")
with patch("pathlib.Path.home", return_value=Path(_import_storage.name)):
    from echo import config, session, web


class StorageTests(unittest.TestCase):
    def setUp(self):
        storage = tempfile.TemporaryDirectory(prefix="echo-regression-")
        self.addCleanup(storage.cleanup)
        self.root = Path(storage.name)
        self.enterContext(patch.dict(os.environ, {"ECHO_API_KEY": "", "ECHO_BASE_URL": "", "ECHO_MODEL": ""}))
        defaults = copy.deepcopy(config.DEFAULT_CONFIG)
        self.addCleanup(setattr, config, "DEFAULT_CONFIG", defaults)
        for name, value in {"CONFIG_DIR": self.root, "CONFIG_FILE": self.root / "config.yml"}.items():
            self.enterContext(patch.object(config, name, value))
        self.enterContext(patch.object(session, "SESSION_DIR", self.root / "sessions"))
        for name, value in {
            "BASE_DIR": self.root, "SESSION_DIR": self.root / "sessions", "SKILLS_DIR": self.root / "skills",
            "MCP_FILE": self.root / "mcp.json", "TASKS_FILE": self.root / "tasks.json", "AVATAR_FILE": self.root / "avatar.txt",
        }.items():
            self.enterContext(patch.object(web, name, value))
        web.SESSION_DIR.mkdir()
        web.SKILLS_DIR.mkdir()
        self.client = TestClient(web.app, base_url="http://localhost")
        self.addCleanup(self.client.close)

    def test_load_returns_independent_nested_defaults(self):
        first = config.load_config()
        first["ai"]["model"] = "mutated-model"
        self.assertNotEqual(config.load_config()["ai"]["model"], "mutated-model")

    def test_legacy_session_titles_with_spaces_remain_loadable(self):
        import json
        legacy = session.Session("legacy notes")
        legacy.add_message("user", "synthetic legacy message")
        (web.SESSION_DIR / "legacy notes.json").write_text(json.dumps(legacy.to_dict()), encoding="utf-8")
        loaded = session.load_session("legacy notes")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.messages[0]["content"], "synthetic legacy message")

    def test_underscore_session_files_from_previous_maintenance_remain_loadable(self):
        import json
        previous = session.Session("release notes")
        previous.add_message("user", "synthetic prior session")
        path = web.SESSION_DIR / "release_notes.json"
        path.write_text(json.dumps(previous.to_dict()), encoding="utf-8")
        loaded = session.load_session("release notes")
        self.assertIsNotNone(loaded)
        session.save_session(loaded)
        self.assertTrue(path.exists())
        self.assertFalse((web.SESSION_DIR / "release notes.json").exists())

    def test_web_sessions_include_cli_saved_conversations(self):
        conversation = session.Session("release notes")
        conversation.add_message("user", "synthetic shared session")
        session.save_session(conversation)
        response = self.client.get("/api/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], "release notes")
        loaded = self.client.get("/api/sessions/release%20notes")
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["messages"][0]["content"], "synthetic shared session")

    def test_one_invalid_session_does_not_break_the_session_list(self):
        valid = self.client.post("/api/sessions", json={"title": "valid"}).json()["id"]
        (web.SESSION_DIR / "damaged.json").write_text('{bad: synthetic-invalid-content', encoding="utf-8")
        (web.SESSION_DIR / "invalid-shape.json").write_text('[]', encoding="utf-8")
        (web.SESSION_DIR / "invalid-messages.json").write_text('{"messages":"invalid"}', encoding="utf-8")
        listed = self.client.get("/api/sessions")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["id"] for item in listed.json()], [valid])
        damaged = self.client.get("/api/sessions/damaged")
        self.assertEqual(damaged.status_code, 422)
        self.assertNotIn("synthetic-invalid-content", damaged.text)

    def test_config_display_redacts_nested_list_values_without_mutating_them(self):
        original = {"services": [{"api_key": "synthetic-list-key", "nested": [{"password": "synthetic-list-password"}]}]}
        redacted = config.redacted_config(original)
        self.assertNotIn("synthetic-list-", str(redacted))
        self.assertEqual(original["services"][0]["api_key"], "synthetic-list-key")

    def test_environment_key_does_not_stick_after_environment_removed(self):
        with patch.dict(os.environ, {"ECHO_API_KEY": "synthetic-sensitive-value"}):
            self.assertEqual(config.load_config()["ai"]["api_key"], "synthetic-sensitive-value")
        self.assertEqual(config.load_config()["ai"]["api_key"], "")

    def test_save_does_not_mutate_defaults(self):
        before = copy.deepcopy(config.DEFAULT_CONFIG)
        config.save_config({"ai": {"api_key": "synthetic-value"}})
        self.assertEqual(config.DEFAULT_CONFIG, before)

    def test_environment_credentials_are_not_persisted_by_unrelated_settings_edits(self):
        with patch.dict(os.environ, {"ECHO_API_KEY": "synthetic-ephemeral-key"}):
            current = config.load_config()
            current["ai"]["model"] = "example-model"
            config.save_config(current)
        self.assertNotIn("synthetic-ephemeral-key", config.CONFIG_FILE.read_text())

    def test_short_keys_are_fully_masked(self):
        self.assertNotIn("abc", web._mask_key("abc"))

    def test_config_api_does_not_expose_saved_keys(self):
        config.save_config({"ai": {"api_key": "synthetic-main-key", "tts_api_key": "synthetic-voice-key", "stt_api_key": "synthetic-listen-key"}})
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        for value in ["synthetic-main-key", "synthetic-voice-key", "synthetic-listen-key"]:
            self.assertNotIn(value, response.text)

    def test_config_cli_does_not_print_saved_keys(self):
        from echo.cli import app
        from typer.testing import CliRunner
        config.save_config({"ai": {"api_key": "synthetic-main-key", "tts_api_key": "synthetic-voice-key"}})
        for args in [["config"], ["config", "--show"]]:
            result = CliRunner().invoke(app, args)
            self.assertEqual(result.exit_code, 0)
            self.assertNotIn("synthetic-main-key", result.output)
            self.assertNotIn("synthetic-voice-key", result.output)

    def test_storage_rejects_path_segments(self):
        for value in ["../outside", "..\\outside", "a/b", "a\\b", ".", "..", "x\x00y"]:
            with self.subTest(value=value), self.assertRaises((HTTPException, ValueError)):
                web._session_path(value)

    def test_requests_with_foreign_origins_are_rejected(self):
        result = self.client.post("/api/sessions", headers={"Origin": "https://other.example.invalid"}, json={"title": "cross-origin"})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(list(web.SESSION_DIR.glob("*.json")), [])

    def test_requests_with_foreign_hosts_are_rejected(self):
        response = self.client.get("/api/config", headers={"Host": "other.example.invalid"})
        self.assertEqual(response.status_code, 400)

    def test_session_create_update_and_delete(self):
        created = self.client.post("/api/sessions", json={"title": "test"})
        self.assertEqual(created.status_code, 200)
        identifier = created.json()["id"]
        updated = self.client.put(f"/api/sessions/{identifier}/messages", json={"messages": [{"role": "user", "content": "hello"}]})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.get(f"/api/sessions/{identifier}").json()["messages"][0]["content"], "hello")
        self.assertEqual(self.client.delete(f"/api/sessions/{identifier}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/sessions/{identifier}").status_code, 404)

    def test_provider_failure_does_not_echo_exception_data(self):
        class BrokenProvider:
            async def chat_stream(self, messages):
                raise RuntimeError("synthetic-private-token")
                yield "unreachable"
        with patch.object(web, "create_provider", return_value=BrokenProvider()):
            response = self.client.post("/api/chat", json={"messages": [{"role": "user", "content": "hello"}]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.text)
        self.assertNotIn("synthetic-private-token", response.text)

    def test_switching_provider_uses_its_default_endpoint_and_model(self):
        current = config.load_config()
        current["ai"]["provider"] = "ollama"
        chosen = config.get_provider_config(current)
        self.assertEqual(chosen.base_url, "http://localhost:11434")
        self.assertNotIn("gpt", chosen.model)

    def test_same_origin_requests_succeed(self):
        response = self.client.post("/api/sessions", headers={"Origin": "http://localhost"}, json={"title": "same origin"})
        self.assertEqual(response.status_code, 200)

    def test_mcp_tokens_are_not_returned_and_empty_edits_preserve_them(self):
        response = self.client.post("/api/mcp", json={"name": "fixture", "url": "https://example.invalid/mcp", "token": "synthetic-mcp-token"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("synthetic-mcp-token", response.text)
        identifier = response.json()["id"]
        result = self.client.put(f"/api/mcp/{identifier}", json={"name": "renamed"})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()["token_set"])
        self.assertNotIn("synthetic-mcp-token", self.client.get("/api/mcp").text)

    def test_skill_create_update_and_delete(self):
        response = self.client.post("/api/skills", json={"name": "中文 skill", "content": "synthetic instructions"})
        self.assertEqual(response.status_code, 200)
        identifier = response.json()["id"]
        self.assertEqual(self.client.put(f"/api/skills/{identifier}", json={"enabled": False}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/skills/{identifier}").status_code, 200)
        self.assertEqual(self.client.post("/api/skills", json={}).status_code, 400)

    def test_empty_storage_can_initialize_without_import_writes(self):
        web.SESSION_DIR.rmdir()
        web.SKILLS_DIR.rmdir()
        self.assertEqual(self.client.get("/api/skills").json(), [])
        self.assertEqual(self.client.post("/api/sessions", json={"title": "first"}).status_code, 200)

    def test_remote_cli_binding_is_rejected(self):
        from echo.cli import app
        from typer.testing import CliRunner
        result = CliRunner().invoke(app, ["web", "--host", "0.0.0.0"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("loopback", result.output)


class TuiTests(unittest.IsolatedAsyncioTestCase):
    async def test_tui_starts_without_network_or_personal_storage(self):
        from echo.tui import EchoApp
        with patch("echo.tui.load_config", return_value=copy.deepcopy(config.DEFAULT_CONFIG)):
            app = EchoApp()
            async with app.run_test(size=(100, 35)) as pilot:
                await pilot.pause()
                self.assertTrue(app.is_running)


if __name__ == "__main__":
    unittest.main()
