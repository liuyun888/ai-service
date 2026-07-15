# scripts/07_03_nodes_edges_demo.py
"""07.03 节点与边演示。

【本课要感受的三件事】
1. 三站职责单一，边顺序固定可测
2. 节点只 return 变更字段
3. docs 为空时 need_clarify=True（条件路由铺垫），本课仍走完 generate

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

from app.graphs.pipeline import USE_KNOWLEDGE_TOOL, run_pipeline  # noqa: E402
from app.lessons.m07_03_nodes_edges import (  # noqa: E402
    compiled_ok,
    demo_empty_docs,
    demo_happy_path,
    demo_partial_returns,
    edge_topology,
    node_responsibilities,
)

NOTE_PATH = ROOT / "notes" / "nodes_edges_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("USE_KNOWLEDGE_TOOL =", USE_KNOWLEDGE_TOOL)
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 07.03 节点与边 · 实跑记录\n",
        "",
        f"- USE_KNOWLEDGE_TOOL={USE_KNOWLEDGE_TOOL}",
        "- 拓扑: retrieve → analyze → generate（普通边）",
        "",
    ]

    # ---- STEP 1 · 职责 ----
    print("\n" + "=" * 52, "STEP 1 · 三节点职责（一句话）")
    duties = node_responsibilities()
    for d in duties:
        print(f"  [{d['node']}] {d['duty']}  写→ {d['writes']}")
    assert len(duties) == 3
    print("ASSERT: 三节点职责可说明 → PASS")
    note.append("## STEP 1 · 职责\n")
    note.append("| 节点 | 职责 | 写入字段 |")
    note.append("|------|------|----------|")
    for d in duties:
        note.append(f"| {d['node']} | {d['duty']} | {d['writes']} |")
    note.append("")

    # ---- STEP 2 · 边拓扑 ----
    print("\n" + "=" * 52, "STEP 2 · 边顺序")
    topo = edge_topology()
    for e in topo:
        print(" ", e)
    assert compiled_ok()
    print("ASSERT: 已 compile，拓扑为三站串行 → PASS")
    note.append("## STEP 2 · 边\n")
    for e in topo:
        note.append(f"- {e}")
    note.append("")

    # ---- STEP 3 · 幸福路径 ----
    print("\n" + "=" * 52, "STEP 3 · 幸福路径（有资料）")
    happy = demo_happy_path("退货时效")
    st = happy["state"]
    print("path:", st.get("path"))
    print("docs:", st.get("docs"))
    print("need_clarify:", st.get("need_clarify"))
    print("answer:", (st.get("answer") or "")[:180])
    assert st.get("path") == ["retrieve", "analyze", "generate"]
    assert st.get("need_clarify") is False
    assert st.get("docs"), "应检索到片段"
    assert "基于资料" in (st.get("answer") or "")
    print("ASSERT: 顺序正确且有 answer → PASS")
    note.append("## STEP 3 · 幸福路径\n")
    note.append(f"- path: `{st.get('path')}`")
    note.append(f"- docs: `{st.get('docs')}`")
    note.append(f"- answer: {st.get('answer')}\n")

    # ---- STEP 4 · 空资料铺垫 ----
    print("\n" + "=" * 52, "STEP 4 · docs 为空（仍走完三站）")
    empty = demo_empty_docs("今天月球天气如何")
    es = empty["state"]
    print("path:", es.get("path"))
    print("docs:", es.get("docs"))
    print("need_clarify:", es.get("need_clarify"))
    print("answer:", (es.get("answer") or "")[:160])
    assert es.get("path") == ["retrieve", "analyze", "generate"]
    assert es.get("need_clarify") is True
    assert "资料不足" in (es.get("answer") or "")
    print("ASSERT: 空 docs 打标仍生成澄清话术 → PASS")
    note.append("## STEP 4 · 空资料\n")
    note.append(f"- need_clarify: {es.get('need_clarify')}")
    note.append(f"- answer: {es.get('answer')}\n")

    # ---- STEP 5 · 只返回补丁 ----
    print("\n" + "=" * 52, "STEP 5 · 节点只返回 PartialState")
    partial = demo_partial_returns()
    print("retrieve_keys:", partial["retrieve_keys"])
    print("analyze_keys:", partial["analyze_keys"])
    print("generate_keys:", partial["generate_keys"])
    assert "query" not in partial["retrieve_keys"]  # 未改的字段不必原样交回
    assert "answer" in partial["generate_keys"]
    print("ASSERT: 返回键为变更子集 → PASS")
    note.append("## STEP 5 · PartialState\n")
    note.append(f"- retrieve → `{partial['retrieve_keys']}`")
    note.append(f"- analyze → `{partial['analyze_keys']}`")
    note.append(f"- generate → `{partial['generate_keys']}`\n")

    # ---- STEP 6 · 可替换标注 ----
    print("\n" + "=" * 52, "STEP 6 · mock/Tool 可替换点")
    src = (ROOT / "app" / "graphs" / "pipeline.py").read_text(encoding="utf-8")
    assert "可替换" in src
    print("USE_KNOWLEDGE_TOOL:", USE_KNOWLEDGE_TOOL)
    print("文件含「可替换」标注 → 真实检索接入点已标出")
    # 再跑一句确认 invoke 始终有 answer
    again = run_pipeline("质保多久")
    assert again.get("answer")
    print("质保 query answer 前 80 字:", (again.get("answer") or "")[:80])
    print("ASSERT: 可替换点存在且 invoke 有 answer → PASS")
    note.append("## STEP 6 · 可替换\n")
    note.append("- `retrieve` 内标注「可替换为真实 Retriever / search_knowledge」")
    note.append(f"- 质保样例 answer: {again.get('answer')}\n")

    note.append("## 结论\n")
    note.append("- 宏观路径用边钉死；局部探索可放在单节点内 Loop。")
    note.append("- need_clarify 已写入 State，下一课用条件边分流。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: nodes_edges 验收通过")


if __name__ == "__main__":
    main()
