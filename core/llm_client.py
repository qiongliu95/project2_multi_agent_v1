"""
Unified LLM client.

The project calls an OpenAI-compatible chat-completions API. DeepSeek is
supported by setting LLM_BASE_URL/OPENAI_BASE_URL and LLM_MODEL/MODEL_NAME.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)


api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("LLM_MODEL") or os.getenv("MODEL_NAME") or "deepseek-chat"
request_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS") or "120")
max_retries = int(os.getenv("LLM_MAX_RETRIES") or "2")
retry_delay_seconds = float(os.getenv("LLM_RETRY_DELAY_SECONDS") or "1")
http_backend = (os.getenv("LLM_HTTP_BACKEND") or "httpx").lower()
trust_env = (os.getenv("LLM_TRUST_ENV") or "true").lower() not in {"0", "false", "no"}


def _default_base_url() -> str:
    if model_name.startswith("deepseek"):
        return "https://api.deepseek.com/v1"
    return "https://api.openai.com/v1"


def _chat_completions_url(raw_base_url: str | None) -> str:
    normalized = (raw_base_url or _default_base_url()).rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def get_client_info() -> Dict[str, Any]:
    """
    Return non-secret client settings for diagnostics.
    """
    return {
        "model": model_name,
        "url": _chat_completions_url(base_url),
        "http_backend": http_backend,
        "trust_env": trust_env,
        "timeout_seconds": request_timeout,
        "max_retries": max_retries,
        "has_api_key": bool(api_key),
    }


def build_prompt(prompt_template: str, payload: Dict[str, Any]) -> str:
    return (
        f"{prompt_template}\n\n"
        "Input:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _build_request_payload(prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": build_prompt(prompt, payload),
            }
        ],
        "temperature": 0,
    }


def _extract_message_content(response_json: Dict[str, Any]) -> str:
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            "LLM response does not contain choices[0].message.content"
        ) from error
    return content.strip() if content else ""


def _call_llm_with_httpx(prompt: str, payload: Dict[str, Any]) -> str:
    try:
        import httpx
    except ImportError as error:
        raise RuntimeError(
            "httpx is not installed. Set LLM_HTTP_BACKEND=urllib or install httpx."
        ) from error

    try:
        with httpx.Client(timeout=request_timeout, trust_env=trust_env) as client:
            response = client.post(
                _chat_completions_url(base_url),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=_build_request_payload(prompt, payload),
            )
            response.raise_for_status()
            return _extract_message_content(response.json())
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"LLM HTTP error {error.response.status_code}: {error.response.text}"
        ) from error
    except httpx.HTTPError as error:
        info = get_client_info()
        raise RuntimeError(
            "LLM request failed via httpx: "
            f"{error}. url={info['url']} model={info['model']} "
            f"trust_env={info['trust_env']}"
        ) from error


def _call_llm_with_urllib(prompt: str, payload: Dict[str, Any]) -> str:
    request = urllib.request.Request(
        url=_chat_completions_url(base_url),
        data=json.dumps(
            _build_request_payload(prompt, payload),
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            response_json = json.loads(response.read().decode("utf-8"))
            return _extract_message_content(response_json)
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"LLM HTTP error {error.code}: {error_body}"
        ) from error
    except urllib.error.URLError as error:
        info = get_client_info()
        raise RuntimeError(
            "LLM request failed via urllib: "
            f"{error.reason}. url={info['url']} model={info['model']}"
        ) from error


def call_llm(prompt: str, payload: Dict[str, Any]) -> str:
    """
    Call an OpenAI-compatible chat-completions endpoint and return text content.
    """
    if not api_key:
        raise ValueError(
            "未读取到 API Key，请检查 .env 中的 LLM_API_KEY 或 OPENAI_API_KEY"
        )

    if http_backend == "urllib":
        call_once = _call_llm_with_urllib
    elif http_backend == "httpx":
        call_once = _call_llm_with_httpx
    else:
        raise ValueError(
            f"Unsupported LLM_HTTP_BACKEND={http_backend}. Use 'httpx' or 'urllib'."
        )

    attempts = max(1, max_retries + 1)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return call_once(prompt, payload)
        except RuntimeError as error:
            last_error = error
            if attempt >= attempts or not _is_retryable_llm_error(error):
                raise
            time.sleep(retry_delay_seconds * attempt)

    raise last_error or RuntimeError("LLM request failed without an exception")


def _is_retryable_llm_error(error: RuntimeError) -> bool:
    message = str(error).lower()
    retryable_markers = [
        "unexpected_eof",
        "incomplete chunked read",
        "peer closed connection",
        "connection reset",
        "connection aborted",
        "10060",
        "连接尝试失败",
        "没有正确答复",
        "主机没有反应",
        "read timed out",
        "timeout",
        "temporarily unavailable",
        "too many requests",
        "502",
        "503",
        "504",
    ]
    return any(marker in message for marker in retryable_markers)
