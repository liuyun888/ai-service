# scripts/07_02_stategraph_basics_demo.py
"""07.02 StateGraph 基础演示。

【本课要感受的三件事】
1. compile + invoke 跑通 Hello：hello graph → HELLO GRAPH
2. 节点只返回变更字段
3. 有/无 reducer：notes 追加 vs 被后写覆盖

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

from app.graphs.hello_graph import run_hello  # noqa: E402
from app.lessons.m07_02_stategraph_basics import (  # noqa: E402
    demo_hello,
    demo_reducer_append,
    demo_reducer_overwrite,
    explain_merge,
)

NOTE_PATH = ROOT / "notes" / "stategraph_basics_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("需已安装 langgraph；cwd 应在 ai-service")
    print("ROOT =", ROOT)

    note: list[str] = [
        "# 07.02 StateGraph 基础 · 实跑记录\n",
        "",
        "## 生命周期\n",
        "```text",
        "定义 State → StateGraph → add_node → add_edge → compile → invoke",
        "```",
        "",
    ]

    # ---- STEP 1 · Hello ----
    print("\n" + "=" * 52, "STEP 1 · Hello 图：compile + invoke")
    hello = demo_hello()
    print("input :", hello["input"])
    print("output:", hello["output"])
    assert hello["output"]["text"] == "HELLO GRAPH"
    # 再直接调一次，对齐课文
    assert run_hello("hi")["text"] == "HI"
    print("ASSERT: 大写文本正确 → PASS")
    note.append("## STEP 1 · Hello\n")
    note.append(f"- input: `{hello['input']}`")
    note.append(f"- output: `{hello['output']}`")
    note.append(f"- lesson: {hello['lesson']}\n")

    # ---- STEP 2 · 合并规则口述要点 ----
    print("\n" + "=" * 52, "STEP 2 · 节点返回如何合并进 State")
    tips = explain_merge()
    for t in tips:
        print(" -", t)
    assert len(tips) >= 3
    print("ASSERT: 合并要点可列出 → PASS")
    note.append("## STEP 2 · 合并要点\n")
    for t in tips:
        note.append(f"- {t}")
    note.append("")

    # ---- STEP 3 · reducer 正例 ----
    print("\n" + "=" * 52, "STEP 3 · reducer 追加（正例）")
    good = demo_reducer_append()
    print("output:", good["output"])
    print("notes_len:", good["notes_len"])
    assert good["notes_len"] == 2
    assert "intake" in good["output"]["notes"][0]
    assert "check" in good["output"]["notes"][1]
    print("ASSERT: notes 两条都在 → PASS")
    note.append("## STEP 3 · reducer 追加\n")
    note.append(f"- `{good['output']}`\n")

    # ---- STEP 4 · 无 reducer 反例 ----
    print("\n" + "=" * 52, "STEP 4 · 无 reducer（反例：后写覆盖）")
    bad = demo_reducer_overwrite()
    print("output:", bad["output"])
    print("notes_len:", bad["notes_len"])
    assert bad["notes_len"] == 1
    assert "intake" not in (bad["output"]["notes"][0] if bad["output"]["notes"] else "")
    assert "只有我" in bad["output"]["notes"][0]
    print("ASSERT: intake 笔记被覆盖 → PASS")
    note.append("## STEP 4 · 覆盖反例\n")
    note.append(f"- `{bad['output']}`")
    note.append(f"- lesson: {bad['lesson']}\n")

    # ---- STEP 5 · 字段自解释 ----
    print("\n" + "=" * 52, "STEP 5 · State 字段可读性检查")
    from app.graphs.hello_graph import HelloState, NotesState

    assert "text" in HelloState.__annotations__
    assert "notes" in NotesState.__annotations__
    print("HelloState fields:", list(HelloState.__annotations__))
    print("NotesState fields:", list(NotesState.__annotations__))
    print("ASSERT: TypedDict 字段齐全 → PASS")
    note.append("## STEP 5 · State 字段\n")
    note.append(f"- HelloState: `{list(HelloState.__annotations__)}`")
    note.append(f"- NotesState: `{list(NotesState.__annotations__)}`\n")

    note.append("## 结论\n")
    note.append("- State + compile 后的图 = 最小可运行单元。")
    note.append("- 列表字段必须声明合并规则，否则后写覆盖。")
    note.append("- 下一课：扩成检索 → 分析 → 生成三节点流水线。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: stategraph_basics 验收通过")


if __name__ == "__main__":
    main()
