# app/lessons/m10_04_internal_auth.py
"""课次 10.04 · ai-service 内部鉴权验收（TestClient）。"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.config import INTERNAL_TOKEN
from app.main import app

# 演示用标准头（模拟 BFF 注入后的样子）
DEMO_HEADERS = {
    "X-Internal-Token": INTERNAL_TOKEN,
    "X-Tenant-Id": "tenant-a",
    "X-User-Id": "u-alice",
    "X-Model-Id": "default",
    "X-Request-Id": "req-demo-001",
}


def demo_missing_internal_token() -> dict[str, Any]:
    """直打无内部令牌 → 401。"""
    client = TestClient(app)
    r = client.get("/v1/context/echo", headers={"X-Tenant-Id": "tenant-a"})
    return {"status_code": r.status_code, "detail": r.json()}


def demo_missing_tenant() -> dict[str, Any]:
    """有内部令牌但缺租户 → 400。"""
    client = TestClient(app)
    r = client.get(
        "/v1/context/echo",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
    )
    return {"status_code": r.status_code, "detail": r.json()}


def demo_echo_ok() -> dict[str, Any]:
    """合法头 → 回显租户与 request_id。"""
    client = TestClient(app)
    r = client.get("/v1/context/echo", headers=DEMO_HEADERS)
    body = r.json() if r.status_code == 200 else {}
    return {"status_code": r.status_code, "body": body}


def demo_stream_done_carries_context() -> dict[str, Any]:
    """SSE done 事件应带上可信上下文。"""
    import json

    client = TestClient(app)
    with client.stream(
        "POST",
        "/v1/chat/stream",
        json={"message": "hi"},
        headers={**DEMO_HEADERS, "Accept": "text/event-stream"},
    ) as resp:
        raw = "".join(resp.iter_text())
        status = resp.status_code

    done: dict[str, Any] = {}
    for block in raw.split("\n\n"):
        line = block.strip()
        if not line.startswith("data:"):
            continue
        payload = json.loads(line[5:].strip())
        if payload.get("type") == "done":
            done = payload
            break
    return {"status_code": status, "done": done, "raw_tail": raw[-200:]}


def demo_suite() -> dict[str, Any]:
    missing = demo_missing_internal_token()
    no_tenant = demo_missing_tenant()
    echo = demo_echo_ok()
    streamed = demo_stream_done_carries_context()
    ok = (
        missing["status_code"] == 401
        and no_tenant["status_code"] == 400
        and echo["status_code"] == 200
        and echo["body"].get("tenant_id") == "tenant-a"
        and echo["body"].get("request_id") == "req-demo-001"
        and streamed["status_code"] == 200
        and streamed["done"].get("tenant_id") == "tenant-a"
        and streamed["done"].get("request_id") == "req-demo-001"
    )
    return {
        "missing_token": missing,
        "missing_tenant": no_tenant,
        "echo": echo,
        "stream": streamed,
        "ok": ok,
    }
