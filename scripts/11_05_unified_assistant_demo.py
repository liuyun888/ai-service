# scripts/11_05_unified_assistant_demo.py
"""课次 11.05 · 统一助手串联验收（离线单元 + 可选 HTTP 流）。

工作目录：ai-service/
用法：
  python scripts/11_05_unified_assistant_demo.py
  # 若本机 8091 已起：
  LIVE=1 python scripts/11_05_unified_assistant_demo.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m11_05_unified_assistant import choose_mode, run_unified_turn


def assert_route() -> None:
    """意图路由表：助手 / 客服 / 工单 / 知识库。"""
    assert choose_mode("防水款还有吗？退货多久？") == "assistant"
    assert choose_mode("你们太坑了要投诉转人工") == "cs"
    assert choose_mode("我的订单 SF123456 到哪了") == "cs"
    assert choose_mode("申请退货工单：外包装破损要求全额退款") == "workflow"
    assert choose_mode("请直接回复用户：保证明天一定退款到账") == "kb"
    print("ASSERT: choose_mode 四路分流 → PASS")


def assert_assistant() -> None:
    out = run_unified_turn(
        "防水款还有吗？退货多久？",
        tenant_id="tenant-a",
        session_id="demo-assist",
    )
    assert out["mode"] == "assistant"
    assert out["ok"]
    assert "mock" not in (out["reply"] or "").lower() or "收到" not in out["reply"]
    # 库存或政策应出现在回复/证据里
    blob = out["reply"] + json.dumps(out.get("evidence") or {}, ensure_ascii=False)
    assert "12" in blob or "库存" in blob or "退" in out["reply"]
    print("ASSERT: assistant 模式有实质回答 → PASS")
    print("  reply[:120]=", (out["reply"] or "")[:120])


def assert_cs_handoff() -> None:
    out = run_unified_turn(
        "你们太坑了要投诉转人工",
        tenant_id="tenant-a",
        session_id="demo-cs",
    )
    assert out["mode"] == "cs"
    assert out["action"] == "handoff"
    assert out.get("summary")
    print("ASSERT: cs handoff + summary → PASS")


def assert_workflow() -> None:
    out = run_unified_turn(
        "申请退货工单：外包装破损要求全额退款",
        tenant_id="tenant-a",
        session_id="demo-wf",
    )
    assert out["mode"] == "workflow"
    assert out.get("case_id")
    assert "退货工单" in out["reply"] or "case_id" in out["reply"]
    print("ASSERT: workflow 创建 case → PASS", out.get("case_id"))


def live_stream() -> None:
    """可选：打本机 /v1/assistant/stream。"""
    import httpx

    base = os.getenv("AI_BASE", "http://127.0.0.1:8091").rstrip("/")
    token = os.getenv("INTERNAL_TOKEN", "dev-internal-token")
    headers = {
        "X-Internal-Token": token,
        "X-Tenant-Id": "tenant-a",
        "X-User-Id": "u-alice",
        "X-Model-Id": "default",
        "X-Request-Id": "req-11-05",
        "Accept": "text/event-stream",
    }
    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            "POST",
            f"{base}/v1/assistant/stream",
            headers=headers,
            json={"message": "防水款还有吗？退货多久？", "session_id": "live-1"},
        ) as resp:
            assert resp.status_code == 200, resp.text
            raw = "".join(resp.iter_text())
    assert "data:" in raw
    assert "mock 流" not in raw
    assert '"type": "done"' in raw or '"type":"done"' in raw
    print("ASSERT: LIVE /v1/assistant/stream 非 mock → PASS")


def main() -> None:
    print("=" * 52, "11.05 unified assistant")
    assert_route()
    assert_assistant()
    assert_cs_handoff()
    assert_workflow()
    if os.getenv("LIVE", "").strip() == "1":
        live_stream()
    else:
        print("SKIP LIVE（设 LIVE=1 且 8091 已起可测 HTTP）")
    print("ALL PASS")


if __name__ == "__main__":
    main()
