# scripts/07_04_conditional_routing_demo.py
"""07.04 条件路由演示。

【本课要感受的三件事】
1. 路由函数返回节点名，可单测、不靠 Prompt 碰运气
2. 商品 / 订单 / 其他 → 三条不同 path
3. 非法 intent 安全落到澄清

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.graphs.router import run_router  # noqa: E402
from app.lessons.m07_04_conditional_routing import (  # noqa: E402
    demo_three_branches,
    illegal_intent_fallback,
    unit_route_table,
)

NOTE_PATH = ROOT / "notes" / "conditional_routing_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("条件路由对照实验（分类用规则，不调 Chat）")
    print("ROOT =", ROOT)

    note: list[str] = [
        "# 07.04 条件路由 · 实跑记录\n",
        "",
        "```text",
        "classify → product → retrieve → generate",
        "         → order   → order_tool → generate",
        "         → other   → clarify",
        "```",
        "",
    ]

    # ---- STEP 1 · 路由真值表（单测）----
    print("\n" + "=" * 52, "STEP 1 · 路由函数单测（无网络）")
    table = unit_route_table()
    for row in table:
        flag = "OK" if row["ok"] == "True" else "FAIL"
        print(
            f"  [{flag}] {row['query']!r} → intent={row['intent']} route={row['route']}"
        )
        assert row["ok"] == "True", row
    print("ASSERT: 真值表全绿 → PASS")
    note.append("## STEP 1 · 真值表\n")
    note.append("| query | intent | route |")
    note.append("|-------|--------|-------|")
    for row in table:
        note.append(f"| {row['query']} | {row['intent']} | {row['route']} |")
    note.append("")

    # ---- STEP 2 · 非法兜底 ----
    print("\n" + "=" * 52, "STEP 2 · 非法 intent → clarify")
    fb = illegal_intent_fallback()
    print("route_after_classify(hack_refund) =", fb)
    assert fb == "clarify"
    print("ASSERT: 安全默认澄清 → PASS")
    note.append("## STEP 2 · 兜底\n")
    note.append(f"- 非法 intent → `{fb}`\n")

    # ---- STEP 3 · 三路实跑 ----
    print("\n" + "=" * 52, "STEP 3 · 三种输入走不同分支")
    branches = demo_three_branches()
    p, o, u = branches["product"], branches["order"], branches["other"]
    print("product path:", p.get("path"), "|", (p.get("answer") or "")[:80])
    print("order   path:", o.get("path"), "|", (o.get("answer") or "")[:80])
    print("other   path:", u.get("path"), "|", (u.get("answer") or "")[:80])
    assert p["path"] == ["classify", "retrieve", "generate"]
    assert o["path"] == ["classify", "order_tool", "generate"]
    assert u["path"] == ["classify", "clarify"]
    assert (p.get("answer") or "").startswith("[检索]")
    assert (o.get("answer") or "").startswith("[Tool]")
    assert "商品" in (u.get("answer") or "") or "订单" in (u.get("answer") or "")
    print("ASSERT: path 与 answer 前缀可区分三路 → PASS")
    note.append("## STEP 3 · 三路\n")
    for name, st in branches.items():
        note.append(f"### {name}\n")
        note.append(f"- path: `{st.get('path')}`")
        note.append(f"- intent: `{st.get('intent')}`")
        note.append(f"- answer: {st.get('answer')}\n")

    # ---- STEP 4 · 课文三句样例 ----
    print("\n" + "=" * 52, "STEP 4 · 课文样例复现")
    samples = ["这款鞋防水吗", "订单 10086 到哪了", "你好"]
    for q in samples:
        out = run_router(q)
        print(f"  {q!r} => intent={out.get('intent')} path={out.get('path')}")
        assert out.get("intent")
        assert out.get("path", [None])[0] == "classify"
    # 防水可能知识库空，但仍应走 retrieve 路径
    shoe = run_router("这款鞋防水吗")
    assert "retrieve" in shoe["path"]
    order = run_router("订单 10086 到哪了")
    assert "SF123456" in (order.get("tool_obs") or "") or "已发货" in (
        order.get("answer") or ""
    )
    print("ASSERT: 课文三句路径符合预期 → PASS")
    note.append("## STEP 4 · 课文样例\n")
    for q in samples:
        out = run_router(q)
        note.append(f"- `{q}` → `{out.get('path')}` / `{out.get('answer')}`")
    note.append("")

    # ---- STEP 5 · 宏观 vs 微观 ----
    print("\n" + "=" * 52, "STEP 5 · 图路由 vs Agent 选 Tool")
    tips = [
        "图路由：宏观走哪条业务链（product/order/other）",
        "Agent 选 Tool：链内局部探索（一节点内 Loop）",
        "不要用「挂 20 个 Tool」代替两条清晰业务边",
    ]
    for t in tips:
        print(" -", t)
    print("ASSERT: 心智区分可口述 → PASS")
    note.append("## STEP 5 · 心智\n")
    for t in tips:
        note.append(f"- {t}")
    note.append("")

    note.append("## 结论\n")
    note.append("- 条件边返回节点名；intent 落 State 便于 Trace。")
    note.append("- 换 LLM 分类时保留 route_after_classify 接口。")
    note.append("- 下一课：Checkpointer + thread_id 续跑。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: conditional_routing 验收通过")


if __name__ == "__main__":
    main()
