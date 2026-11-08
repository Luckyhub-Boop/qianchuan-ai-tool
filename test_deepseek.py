from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import deepseek_client


class DeepSeekTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_path = Path(self.temp.name) / "deepseek.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "baseUrl": "https://example.test",
                    "chatEndpoint": "/chat/completions",
                    "apiKeyEnv": "TEST_DEEPSEEK_KEY",
                    "models": {
                        "development": {"id": "deepseek-v4-pro"},
                        "product": {"id": "deepseek-flash"},
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_status_never_exposes_api_key(self) -> None:
        with patch.dict(os.environ, {"TEST_DEEPSEEK_KEY": "secret-value"}):
            status = deepseek_client.DeepSeekClient(self.config_path).status()
        self.assertTrue(status["configured"])
        self.assertEqual(status["productModel"], "deepseek-flash")
        self.assertEqual(status["developmentModel"], "deepseek-v4-pro")
        self.assertNotIn("secret-value", json.dumps(status))
        self.assertNotIn("apiKey", status)

    def test_product_generation_is_locked_to_flash(self) -> None:
        with patch.dict(os.environ, {"TEST_DEEPSEEK_KEY": "secret-value"}):
            client = deepseek_client.DeepSeekClient(self.config_path)
        with patch(
            "deepseek_client.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            response = client.generate([{"role": "user", "content": "test"}])
        self.assertFalse(response["ok"])
        self.assertEqual(response["model"], "deepseek-flash")

    def test_missing_key_falls_back_without_network(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            client = deepseek_client.DeepSeekClient(self.config_path)
        result = client.generate([{"role": "user", "content": "test"}])
        self.assertFalse(result["ok"])
        self.assertEqual(result["mode"], "local_fallback")
        self.assertIn("DEEPSEEK_API_KEY", result["error"])

    def test_request_body_uses_flash_for_product_calls(self) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps(
                    {
                        "model": "deepseek-flash",
                        "choices": [{"message": {"content": "依据[1]，建议控量。"}}],
                        "usage": {"total_tokens": 12},
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch.dict(os.environ, {"TEST_DEEPSEEK_KEY": "secret-value"}):
            client = deepseek_client.DeepSeekClient(self.config_path)
        with patch("deepseek_client.urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.generate([{"role": "user", "content": "test"}])

        self.assertTrue(result["ok"])
        self.assertEqual(captured["body"]["model"], "deepseek-flash")
        self.assertEqual(result["model"], "deepseek-flash")


if __name__ == "__main__":
    unittest.main()
