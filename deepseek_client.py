from __future__ import annotations

import copy
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "data" / "deepseek.json"
EXAMPLE_CONFIG_PATH = ROOT / "deepseek.config.example.json"
DEVELOPMENT_MODEL = "deepseek-v4-pro"
PRODUCT_MODEL = "deepseek-flash"


class DeepSeekError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def load_config(path: Path | None = None) -> dict[str, Any]:
    configured_path = os.getenv("DEEPSEEK_CONFIG_PATH", "").strip()
    target = path or (Path(configured_path) if configured_path else DEFAULT_CONFIG_PATH)
    value = _read_json(target)
    if not value and target != EXAMPLE_CONFIG_PATH:
        value = _read_json(EXAMPLE_CONFIG_PATH)
    models = value.get("models") if isinstance(value.get("models"), dict) else {}
    development = models.get("development") if isinstance(models.get("development"), dict) else {}
    product = models.get("product") if isinstance(models.get("product"), dict) else {}
    development_model = str(
        os.getenv("DEEPSEEK_DEVELOPMENT_MODEL", "")
        or development.get("id")
        or DEVELOPMENT_MODEL
    ).strip()
    product_model = str(
        os.getenv("DEEPSEEK_PRODUCT_MODEL", "")
        or product.get("id")
        or PRODUCT_MODEL
    ).strip()
    value["models"] = {
        **models,
        "development": {**development, "id": development_model},
        "product": {**product, "id": product_model},
    }
    value["baseUrl"] = str(
        os.getenv("DEEPSEEK_BASE_URL", "") or value.get("baseUrl") or ""
    ).strip()
    value["chatEndpoint"] = str(value.get("chatEndpoint") or "/chat/completions").strip()
    value["apiKeyEnv"] = str(value.get("apiKeyEnv") or "DEEPSEEK_API_KEY").strip()
    value["timeoutSeconds"] = max(
        3.0,
        float(value.get("timeoutSeconds") or 30),
    )
    value["maxTokens"] = max(64, int(value.get("maxTokens") or 900))
    value["temperature"] = max(0.0, min(2.0, float(value.get("temperature") or 0.2)))
    return value


class DeepSeekClient:
    """OpenAI-compatible DeepSeek client with separate development/product models."""

    def __init__(self, path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.path = path or DEFAULT_CONFIG_PATH
        self.config = copy.deepcopy(config or load_config(path))
        self.api_key = str(
            os.getenv(str(self.config.get("apiKeyEnv") or "DEEPSEEK_API_KEY"), "")
            or self.config.get("apiKey")
            or ""
        ).strip()
        self.base_url = str(self.config.get("baseUrl") or "").strip().rstrip("/")
        self.chat_endpoint = str(
            self.config.get("chatEndpoint") or "/chat/completions"
        ).strip()
        if self.chat_endpoint.startswith("http"):
            self.endpoint = self.chat_endpoint
        else:
            self.endpoint = (
                self.base_url
                + ("" if self.chat_endpoint.startswith("/") else "/")
                + self.chat_endpoint
            )

    def model_id(self, purpose: str = "product") -> str:
        if purpose not in {"product", "development"}:
            raise ValueError("DeepSeek purpose 必须是 product 或 development")
        models = self.config.get("models") if isinstance(self.config.get("models"), dict) else {}
        entry = models.get(purpose) if isinstance(models.get(purpose), dict) else {}
        default = PRODUCT_MODEL if purpose == "product" else DEVELOPMENT_MODEL
        return str(entry.get("id") or default).strip()

    def status(self) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(self.endpoint)
        configured = bool(
            self.config.get("enabled", True)
            and parsed.scheme == "https"
            and parsed.netloc
            and self.api_key
        )
        return {
            "ok": configured,
            "configured": configured,
            "enabled": bool(self.config.get("enabled", True)),
            "baseUrlConfigured": bool(parsed.netloc),
            "apiKeyConfigured": bool(self.api_key),
            "endpointHost": parsed.netloc,
            "developmentModel": self.model_id("development"),
            "productModel": self.model_id("product"),
            "productModelLocked": self.model_id("product") == PRODUCT_MODEL,
            "mode": "deepseek" if configured else "local_fallback",
            "error": (
                ""
                if configured
                else "DeepSeek 未配置：请设置 DEEPSEEK_API_KEY，并确认 baseUrl 可访问"
            ),
        }

    def _sanitize(self, value: str) -> str:
        text = str(value or "")
        if self.api_key:
            text = text.replace(self.api_key, "[redacted]")
        return text[:1200]

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        purpose: str = "product",
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        status = self.status()
        if not status["configured"]:
            return {
                "ok": False,
                "model": self.model_id(purpose),
                "mode": "local_fallback",
                "error": status["error"],
            }
        body = {
            "model": self.model_id(purpose),
            "messages": copy.deepcopy(messages),
            "temperature": (
                self.config["temperature"] if temperature is None else max(0.0, min(2.0, temperature))
            ),
            "max_tokens": max_tokens or self.config["maxTokens"],
            "stream": False,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Qianchuan-AI-Dashboard-DeepSeek/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=float(self.config.get("timeoutSeconds") or 30),
            ) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "model": body["model"],
                "mode": "local_fallback",
                "error": self._sanitize(f"DeepSeek HTTP {exc.code}: {message or exc.reason}"),
            }
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return {
                "ok": False,
                "model": body["model"],
                "mode": "local_fallback",
                "error": self._sanitize(f"DeepSeek 调用失败：{exc}"),
            }
        choices = payload.get("choices") if isinstance(payload, dict) else []
        first = choices[0] if isinstance(choices, list) and choices else {}
        message = first.get("message") if isinstance(first, dict) else {}
        text = str(message.get("content") or "").strip() if isinstance(message, dict) else ""
        if not text:
            return {
                "ok": False,
                "model": body["model"],
                "mode": "local_fallback",
                "error": "DeepSeek 返回空内容",
            }
        return {
            "ok": True,
            "model": body["model"],
            "responseModel": str(payload.get("model") or body["model"]),
            "mode": "deepseek",
            "text": text,
            "usage": copy.deepcopy(payload.get("usage") or {}),
            "error": "",
        }
