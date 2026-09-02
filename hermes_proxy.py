#!/usr/bin/env python
# Минимальный OpenAI-совместимый HTTP-прокси, который прикрепляет
# OPENROUTER_API_KEY (или любой *_API_KEY) к запросам и пересылает их
# на Upstream URL. Используется на Render вместо `hermes proxy`, потому
# что тот работает только с OAuth-провайдерами Nous/xAI, а нам нужен
# произвольный ключ.
#
# Эндпоинты:
#   GET  /v1/models          — статический ответ со списком моделей
#   POST /v1/chat/completions — проксирует на $UPSTREAM_BASE_URL/chat/completions
#   POST /v1/completions     — проксирует на $UPSTREAM_BASE_URL/completions
#   GET  /                   — healthcheck
#
# Переменные окружения:
#   OPENROUTER_API_KEY (или OPENAI_API_KEY, или ANTHROPIC_API_KEY)
#   HERMES_MODEL               — модель по умолчанию
#   UPSTREAM_BASE_URL          — по умолчанию https://openrouter.ai/api/v1
#   UPSTREAM_API_KEY_HEADER    — по умолчанию Authorization: Bearer
"""Minimal OpenAI-compatible HTTP proxy for Render / any container host."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "info"))
log = logging.getLogger("hermes-proxy")

# === Конфигурация из окружения =================================================
API_KEYS = [
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
    ("OPENAI_API_KEY",     "https://api.openai.com/v1"),
    ("ANTHROPIC_API_KEY",  "https://api.anthropic.com/v1"),
    ("GROQ_API_KEY",       "https://api.groq.com/openai/v1"),
    ("GOOGLE_API_KEY",     "https://generativelanguage.googleapis.com/v1beta"),
]

UPSTREAM_BASE_URL = os.environ.get("UPSTREAM_BASE_URL")
UPSTREAM_API_KEY = None

for name, default_base in API_KEYS:
    val = os.environ.get(name)
    if val:
        UPSTREAM_API_KEY = val
        if not UPSTREAM_BASE_URL:
            UPSTREAM_BASE_URL = default_base
        log.info("using provider key %s -> %s", name, UPSTREAM_BASE_URL)
        break

if not UPSTREAM_API_KEY:
    log.warning("no *_API_KEY in env — proxy will return 401 on chat/completions")

DEFAULT_MODEL = os.environ.get("HERMES_MODEL", "openrouter/auto")

# === Приложение ================================================================
app = FastAPI(title="Hermes OpenAI Proxy", version="0.1.0")

# Один общий клиент — переиспользует соединения, важно для стриминга.
client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=300.0))


def _model_card(model_id: str) -> dict[str, Any]:
    return {
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "hermes-deploy",
    }


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "hermes-openai-proxy",
        "upstream": UPSTREAM_BASE_URL,
        "default_model": DEFAULT_MODEL,
        "has_api_key": bool(UPSTREAM_API_KEY),
    }


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    models = [_model_card(DEFAULT_MODEL)]
    if "/" in DEFAULT_MODEL:
        # Если модель вида provider/model — отдаём оба варианта для удобства клиентов.
        models.append(_model_card(DEFAULT_MODEL.split("/", 1)[1]))
    return {"object": "list", "data": models}


async def _proxy_request(path: str, request: Request) -> Response:
    if not UPSTREAM_API_KEY:
        return Response(
            content=json.dumps({"error": "no API key configured"}),
            status_code=401,
            media_type="application/json",
        )

    body = await request.body()
    # Если клиент не указал модель — подставляем нашу.
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return Response(
            content=json.dumps({"error": "invalid JSON body"}),
            status_code=400,
            media_type="application/json",
        )
    if isinstance(payload, dict) and "model" not in payload:
        payload["model"] = DEFAULT_MODEL

    url = (UPSTREAM_BASE_URL or "").rstrip("/") + path
    headers = dict(request.headers)
    headers["authorization"] = f"Bearer {UPSTREAM_API_KEY}"
    headers["host"] = httpx.URL(url).host
    # Не прокидываем content-length — httpx выставит сам.
    headers.pop("content-length", None)

    is_stream = bool(payload.get("stream"))

    upstream_req = client.build_request(
        method=request.method,
        url=url,
        headers=headers,
        content=json.dumps(payload).encode("utf-8"),
    )

    if is_stream:
        # Стрим: собираем куски и сразу отдаём клиенту.
        async def _relay():
            async with client.stream(
                upstream_req.method, upstream_req.url,
                headers=upstream_req.headers, content=upstream_req.content,
            ) as r:
                async for chunk in r.aiter_bytes():
                    yield chunk
        return Response(content=_relay(), media_type="text/event-stream")

    upstream_resp = await client.send(upstream_req)
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=dict(upstream_resp.headers),
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    return await _proxy_request("/chat/completions", request)


@app.post("/v1/completions")
async def completions(request: Request) -> Response:
    return await _proxy_request("/completions", request)


@app.post("/v1/embeddings")
async def embeddings(request: Request) -> Response:
    return await _proxy_request("/embeddings", request)


@app.on_event("shutdown")
async def _shutdown() -> None:
    await client.aclose()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")