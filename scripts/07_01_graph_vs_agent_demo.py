# scripts/07_01_graph_vs_agent_demo.py
"""07.01 图 vs 单 Agent 演示。

【本课要感受的三件事】
1. 选型清单可算分：≥2 条信号才上图
2. FAQ / 查库存 → 单 Agent 短链路足够
3. 退货多阶段 → 状态图 path 可回放，且标 needs_human

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

from app.lessons.m07_01_graph_vs_agent import (  # noqa: E402
    CRITERIA,
    contrast_pair,
    run_faq_as_agent,
    run_return_as_graph,
    run_stock_as_agent,
    score_scenarios,
)

NOTE_PATH = ROOT / "notes" / "graph_vs_agent_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("本课对照实验（默认不调 Chat）；需已安装 langgraph")
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 07.01 图 vs 单 Agent · 实跑记录\n",
        "",
        "## 选型清单（勾选 ≥2 再上图）\n",
    ]
    for key, label in CRITERIA:
        note.append(f"- `{key}`: {label}")
    note.append("")

    # ---- STEP 1 · 清单 ----
    print("\n" + "=" * 52, "STEP 1 · 选型清单（贴墙版）")
    for key, label in CRITERIA:
        print(f"  [ ] {key}: {label}")
    assert len(CRITERIA) == 5
    print("ASSERT: 五条清单齐全 → PASS")

    # ---- STEP 2 · 五场景打分 ----
    print("\n" + "=" * 52, "STEP 2 · 五场景选型表")
    rows = score_scenarios()
    print(f"{'场景':<28} | hits | 结论")
    print("-" * 56)
    for r in rows:
        print(f"{r.name:<28} | {r.hits:4} | {r.decision}")
    decisions = {r.decision for r in rows}
    assert "Agent" in decisions
    assert "Graph" in decisions
    assert any(r.decision == "Graph" for r in rows)
    # FAQ / 库存应是 Agent
    by_name = {r.name: r for r in rows}
    assert by_name["包装尺寸 FAQ"].decision == "Agent"
    assert by_name["退货审核（校验→判责→人确认→开单）"].decision == "Graph"
    print("ASSERT: 至少一 Agent、一 Graph；退货上图 → PASS")
    note.append("## STEP 2 · 选型表\n")
    note.append("| 场景 | 命中条数 | 结论 | 说明 |")
    note.append("|------|----------|------|------|")
    for r in rows:
        note.append(f"| {r.name} | {r.hits} | {r.decision} | {r.why} |")
    note.append("")

    # ---- STEP 3 · FAQ Agent ----
    print("\n" + "=" * 52, "STEP 3 · FAQ 走单 Agent")
    faq = run_faq_as_agent("退货几天内可以？")
    print("path:", faq["path"])
    print("answer:", faq["answer"][:160])
    assert faq["mode"] == "single_agent"
    assert "search_knowledge" in faq["path"][1]
    assert "7" in faq["answer"] or "退货" in faq["answer"]
    stock = run_stock_as_agent()
    assert "stock=12" in stock["answer"]
    print("stock:", stock["answer"])
    print("ASSERT: FAQ/库存无图阶段也能答 → PASS")
    note.append("## STEP 3 · 单 Agent\n")
    note.append(f"- FAQ path: `{faq['path']}`")
    note.append(f"- FAQ answer: {faq['answer']}")
    note.append(f"- 库存: {stock['answer']}\n")

    # ---- STEP 4 · 退货图 ----
    print("\n" + "=" * 52, "STEP 4 · 退货走状态图")
    ret = run_return_as_graph("我要退货，订单号 ORD12345")
    print("intent:", ret["intent"])
    print("path:", ret["path"])
    print("needs_human:", ret["needs_human"])
    print("answer:", ret["answer"][:200])
    assert ret["mode"] == "state_graph"
    assert ret["path"][0] == "classify"
    assert "validate_order" in ret["path"]
    assert "await_human" in ret["path"]
    assert "draft_ticket" in ret["path"]
    assert ret["needs_human"] is True
    assert "ORD12345" in ret["order_id"] or "ORD12345" in ret["answer"]
    print("ASSERT: 退货路径含校验/等人/开单草稿 → PASS")
    note.append("## STEP 4 · 状态图\n")
    note.append(f"- path: `{ret['path']}`")
    note.append(f"- needs_human: {ret['needs_human']}")
    note.append(f"- answer: {ret['answer']}\n")

    # ---- STEP 5 · 对照包 ----
    print("\n" + "=" * 52, "STEP 5 · 对照：FAQ Agent vs 退货 Graph")
    pair = contrast_pair()
    print("FAQ path:", pair["faq_agent"]["path"])
    print("Return path:", pair["return_graph"]["path"])
    assert "await_human" not in pair["faq_agent"]["path"]
    assert "await_human" in pair["return_graph"]["path"]
    # FAQ 走图也能跑，但选型结论仍应是 Agent——用另一句政策问图的 faq 分支
    faq_via_graph = run_return_as_graph("包装发货大概多久？")
    print("政策问法走图 path:", faq_via_graph["path"])
    assert faq_via_graph["path"] == ["classify", "faq_answer"]
    print("ASSERT: 对照成立；图也可承载 FAQ，但不等于该上图 → PASS")
    note.append("## STEP 5 · 对照\n")
    note.append(f"- Agent FAQ path: `{pair['faq_agent']['path']}`")
    note.append(f"- Graph return path: `{pair['return_graph']['path']}`")
    note.append(
        f"- 政策口语误走轻量图: `{faq_via_graph['path']}` "
        "（能跑 ≠ 选型该上图）\n"
    )

    # ---- STEP 6 · 反例 ----
    print("\n" + "=" * 52, "STEP 6 · 反例：不该上图")
    anti = "只有查库存数字、无线上审批/暂停 → 单 Agent，不上图"
    print(anti)
    assert by_name["查实时库存"].decision == "Agent"
    print("ASSERT: 反例场景结论为 Agent → PASS")
    note.append("## STEP 6 · 反例\n")
    note.append(f"- {anti}\n")

    note.append("## 结论\n")
    note.append("- 图管宏观路径；Loop 管局部探索——Loop 不会消失。")
    note.append("- ≥2 条信号再上图；先跑通单 Agent 里程碑。")
    note.append("- 下一课：最小 Hello StateGraph（定义 State / compile / invoke）。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: graph_vs_agent 验收通过")


if __name__ == "__main__":
    main()
