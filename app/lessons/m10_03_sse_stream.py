# app/lessons/m10_03_sse_stream.py
"""课次 10.03 · ai-service 侧 SSE 验收（TestClient，不启端口也能跑）。"""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from app.api.chat_stream import TOKEN_INTERVAL_SEC, _sse_data
from app.config import INTERNAL_TOKEN
from app.main import app

# 10.04 起流式接口要内部头；本课演示用固定演示上下文
_DEMO_AUTH_HEADERS = {
    "Accept": "text/event-stream",
    "X-Internal-Token": INTERNAL_TOKEN,
    "X-Tenant-Id": "demo",
    "X-User-Id": "demo-user",
    "X-Model-Id": "default",
    "X-Request-Id": "req-m10-03",
}


def event_contract() -> list[dict[str, str]]:
    """事件约定小抄。"""
    return [
        {"type": "token", "meaning": "文本增量"},
        {"type": "done", "meaning": "正常结束"},
        {"type": "error", "meaning": "出错说明"},
    ]


def demo_stream_tokens(message: str = "退货要几天") -> dict[str, Any]:
    """直连 ai-service /v1/chat/stream，收集事件。"""
    client = TestClient(app)
    # TestClient 同步读流
    with client.stream(
        "POST",
        "/v1/chat/stream",
        json={"message": message},
        headers=_DEMO_AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in (resp.headers.get("content-type") or "")
        raw = "".join(resp.iter_text())

    events: list[dict[str, Any]] = []
    for block in raw.split("\n\n"):
        line = block.strip()
        if not line.startswith("data:"):
            continue
        events.append(json.loads(line[5:].strip()))

    types = [e.get("type") for e in events]
    texts = [e.get("text", "") for e in events if e.get("type") == "token"]
    return {
        "raw_preview": raw[:200],
        "event_types": types,
        "token_count": len(texts),
        "joined": "".join(texts),
        "has_done": "done" in types,
        "interval": TOKEN_INTERVAL_SEC,
        "sample_line": _sse_data({"type": "token", "text": "你"}).strip(),
    }


def demo_suite() -> dict[str, Any]:
    streamed = demo_stream_tokens()
    return {
        "contract": event_contract(),
        "stream": streamed,
        "ok": (
            streamed["token_count"] >= 3
            and streamed["has_done"]
            and "收到" in streamed["joined"]
            and streamed["event_types"][-1] == "done"
        ),
    }
