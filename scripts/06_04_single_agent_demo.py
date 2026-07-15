# scripts/06_04_single_agent_demo.py
"""06.04 单 Agent 落地演示。

【本课要感受的三件事】
1. 组合问题会打到 ≥2 类 Tool（业务状态 + 知识检索）
2. 最终回答拴在 Observation 上，不与工具结果矛盾
3. 同 session 多轮能记住 sku；HTTP /agent/chat 可验收

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m06_04_single_agent import (  # noqa: E402
    DEMO_COMBO,
    DEMO_OFF_TOPIC,
    DEMO_STOCK_ONLY,
    demo_acceptance_suite,
    tool_classes_in_trace,
)
from app.tools.knowledge import search_knowledge  # noqa: E402

NOTE_PATH = ROOT / "notes" / "single_agent_result.md"


def main() -> None:
    use_chat = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
    print("=" * 52, "CONFIG")
    print("USE_CHAT =", int(use_chat), "| 默认脚本化客服（不调 Chat）")
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 06.04 单 Agent 落地 · 实跑记录\n",
        "",
        f"- USE_CHAT={int(use_chat)}",
        "- Tools: `get_inventory` / `get_shipment`（业务状态）+ `search_knowledge`（知识检索）",
        "- HTTP: `POST /agent/chat`",
        "",
    ]

    # ---- STEP 0 · 知识 Tool 可单独 invoke ----
    print("\n" + "=" * 52, "STEP 0 · search_knowledge 单独可调用")
    kn = search_knowledge.invoke({"query": "退货几天内可以"})
    print("observation:", kn[:160])
    assert "7" in kn or "退货" in kn
    assert kn != "not_found"
    print("ASSERT: 知识 Tool 命中退货条款 → PASS")
    note.append("## STEP 0 · search_knowledge\n")
    note.append(f"- `{kn}`\n")

    suite = demo_acceptance_suite(use_chat=use_chat)

    # ---- STEP 1 · 只问库存 ----
    print("\n" + "=" * 52, "STEP 1 · 只问库存 → 仅业务状态类")
    stock = suite["stock_only"]
    print("Q:", DEMO_STOCK_ONLY)
    print("trace:", stock["trace"])
    print("classes:", stock["tool_classes"])
    print("reply:", stock["reply"][:200])
    names = {t["tool"] for t in stock["trace"]}
    assert "get_inventory" in names
    assert "search_knowledge" not in names
    assert "stock=12" in stock["reply"] or any(
        "stock=12" in str(t.get("observation")) for t in stock["trace"]
    )
    print("ASSERT: 仅库存类 Tool，数字与 mock 一致 → PASS")
    note.append("## STEP 1 · 只问库存\n")
    note.append(f"- trace: `{stock['trace']}`")
    note.append(f"- classes: {stock['tool_classes']}")
    note.append(f"- reply: {stock['reply']}\n")

    # ---- STEP 2 · 组合问：两类 Tool ----
    print("\n" + "=" * 52, "STEP 2 · 库存+政策 → ≥2 类 Tool")
    combo = suite["combo"]
    print("Q:", DEMO_COMBO)
    print("trace:", combo["trace"])
    print("classes:", combo["tool_classes"])
    print("reply:", combo["reply"][:240])
    classes = set(combo["tool_classes"]) or tool_classes_in_trace(combo["trace"])
    assert "业务状态" in classes and "知识检索" in classes
    assert "get_inventory" in {t["tool"] for t in combo["trace"]}
    assert "search_knowledge" in {t["tool"] for t in combo["trace"]}
    # 回答不得与观察矛盾：mock 黑耳机是 12
    assert "158" not in combo["reply"]  # 防瞎编常见假数
    print("ASSERT: 两类 Tool + 回答未明显 contradict → PASS")
    note.append("## STEP 2 · 组合问\n")
    note.append(f"- trace: `{combo['trace']}`")
    note.append(f"- classes: {sorted(classes)}")
    note.append(f"- reply: {combo['reply']}\n")

    # ---- STEP 3 · 无关问题拒答 ----
    print("\n" + "=" * 52, "STEP 3 · 无关问题 → 不查库存瞎编")
    off = suite["off_topic"]
    print("Q:", DEMO_OFF_TOPIC)
    print("trace:", off["trace"])
    print("reply:", off["reply"][:200])
    assert off["trace"] == [] or "get_inventory" not in {t["tool"] for t in off["trace"]}
    assert "stock=" not in off["reply"]
    print("ASSERT: 拒答且未伪造库存 → PASS")
    note.append("## STEP 3 · 无关拒答\n")
    note.append(f"- trace: `{off['trace']}`")
    note.append(f"- reply: {off['reply']}\n")

    # ---- STEP 4 · 多轮记忆 ----
    print("\n" + "=" * 52, "STEP 4 · 同 session 多轮记住 sku")
    t1, t2 = suite["memory_turn1"], suite["memory_turn2"]
    print("turn1 reply:", t1["reply"][:120])
    print("turn2 trace:", t2["trace"])
    print("turn2 reply:", t2["reply"][:200])
    assert t2.get("session_sku") == "EARPHONE-PRO-BK" or any(
        (t.get("args") or {}).get("sku") == "EARPHONE-PRO-BK" for t in t2["trace"]
    )
    assert any("stock=12" in str(t.get("observation")) for t in t2["trace"]) or (
        "stock=12" in t2["reply"]
    )
    print("ASSERT: 第二轮靠记忆查到 stock=12 → PASS")
    note.append("## STEP 4 · 多轮记忆\n")
    note.append(f"- turn2 trace: `{t2['trace']}`")
    note.append(f"- turn2 reply: {t2['reply']}\n")

    # ---- STEP 5 · HTTP 契约（TestClient，不需起服务进程）----
    print("\n" + "=" * 52, "STEP 5 · POST /agent/chat（TestClient）")
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/agent/chat",
        json={
            "message": DEMO_COMBO,
            "session_id": "http-demo",
            "tenant_id": "demo",
            "use_chat": False,
        },
    )
    print("status:", r.status_code)
    body = r.json()
    print("tool_classes:", body.get("tool_classes"))
    print("reply:", str(body.get("reply", ""))[:160])
    assert r.status_code == 200
    assert "业务状态" in body["tool_classes"] and "知识检索" in body["tool_classes"]
    assert body["mode"] == "scripted"
    print("ASSERT: /agent/chat 返回两类 Tool 轨迹 → PASS")
    note.append("## STEP 5 · HTTP\n")
    note.append(f"- status: {r.status_code}")
    note.append(f"- tool_classes: {body.get('tool_classes')}")
    note.append(f"- reply: {body.get('reply')}\n")

    note.append("## 结论\n")
    note.append("- 单 Agent = System + ≥2 类 Tool + Loop 限制 +（可选）session 记忆。")
    note.append("- 组合问必须能在 trace 里看到两类工具；回答拴在 Observation 上。")
    note.append("- 下一步（06.05）回炉 Tool 粒度、幂等与错误返回。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: single_agent 验收通过")


if __name__ == "__main__":
    main()
