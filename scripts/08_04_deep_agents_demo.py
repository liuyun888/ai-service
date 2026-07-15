# scripts/08_04_deep_agents_demo.py
"""08.04 Deep Agents 上手与任务规划演示。

【本课要感受的三件事】
1. write_todos → 逐条 mark_done 的完整轨迹
2. max_steps 会截断「拆太细」的 Deep
3. 该 Deep 的任务 vs 不该 Deep 的 FAQ 反例

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

from app.lessons.m08_04_deep_agents import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "deep_agents_result.md"


def main() -> None:
    use_chat = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
    print("=" * 52, "CONFIG")
    print("Deep Agent ≈ 显式 todos + 步进循环 + max_steps")
    print("ROOT =", ROOT)
    print("USE_CHAT =", int(use_chat))

    suite = demo_suite(use_chat=use_chat)
    note: list[str] = [
        "# 08.04 Deep Agents · 实跑记录\n",
        "",
        f"- USE_CHAT={int(use_chat)}",
        f"- goal: {suite['goal']}",
        "",
    ]

    # ---- STEP 1 · 何时 Deep ----
    print("\n" + "=" * 52, "STEP 1 · 该不该 Deep")
    g, f = suite["gate_demo"], suite["gate_faq"]
    print(f"  方案任务 deep={g['deep']} | {g['reason']}")
    print(f"  FAQ       deep={f['deep']} | {f['reason']}")
    print(f"  反例提示: {g['counterexample']}")
    assert g["deep"] is True
    assert f["deep"] is False
    print("ASSERT: 方案 Deep / FAQ 不 Deep → PASS")
    note.append("## STEP 1 · 门禁\n")
    note.append(f"- demo: deep={g['deep']} ({g['reason']})")
    note.append(f"- faq: deep={f['deep']} ({f['reason']})\n")

    # ---- STEP 2 · 完整 todos 轨迹 ----
    print("\n" + "=" * 52, "STEP 2 · 售后改进方案（todos 全勾选）")
    deep = suite["deep"]
    print(f"  goal: {deep.goal}")
    for t in suite["deep_todos"]:
        mark = "x" if t["done"] else " "
        print(f"  [{mark}] #{t['id']} {t['title']}")
    print("  trajectory events:")
    for ev in deep.trajectory:
        print(f"    - {ev.get('event')}")
    print("  final note:")
    print("   ", (deep.notes[-1] if deep.notes else "")[:160])
    assert suite["deep_all_done"]
    assert any(e.get("event") == "write_todos" for e in deep.trajectory)
    assert sum(1 for e in deep.trajectory if e.get("event") == "mark_done") >= 4
    assert deep.steps_used <= deep.max_steps
    assert "return_policy" in "\n".join(deep.notes) or "改进方案大纲" in (deep.notes[-1] if deep.notes else "")
    print("ASSERT: write_todos → 全 done 轨迹齐全 → PASS")
    note.append("## STEP 2 · todos\n")
    for t in suite["deep_todos"]:
        note.append(f"- [{'x' if t['done'] else ' '}] #{t['id']} {t['title']}")
    note.append("")
    note.append("### notes\n")
    for n in deep.notes:
        note.append(f"- {n[:200]}")
    note.append("")

    # ---- STEP 3 · max_steps ----
    print("\n" + "=" * 52, "STEP 3 · max_steps 截断")
    capped = suite["capped"]
    print(f"  steps_used={capped.steps_used} max={capped.max_steps}")
    print(f"  pending ({len(suite['capped_pending'])}): {suite['capped_pending'][:3]}…")
    assert any(e.get("event") == "max_steps" for e in capped.trajectory)
    assert not all(t.done for t in capped.todos)
    print("ASSERT: 拆太细会被 max_steps 拦住 → PASS")
    note.append("## STEP 3 · max_steps\n")
    note.append(f"- used={capped.steps_used}/{capped.max_steps}")
    note.append(f"- pending={suite['capped_pending']}\n")

    # ---- STEP 4 · 浅 vs 深 ----
    print("\n" + "=" * 52, "STEP 4 · 一把梭 vs todos")
    sh = suite["shallow"]
    print(f"  shallow: has_todos={sh['has_todos']} risk={sh['risk']}")
    print(f"  deep:    has_todos=True all_done={suite['deep_all_done']}")
    assert sh["has_todos"] is False
    print("ASSERT: 能说清浅深差异 → PASS")
    note.append("## STEP 4 · 对照\n")
    note.append(f"- shallow risk: {sh['risk']}")
    note.append(f"- deep all_done: {suite['deep_all_done']}\n")

    # ---- STEP 5 · 可选 LLM 规划 ----
    print("\n" + "=" * 52, "STEP 5 · LLM 写 todos（可选）")
    if suite["llm"] is None:
        print("  跳过（USE_CHAT=0）。需要时: USE_CHAT=1 python scripts/08_04_deep_agents_demo.py")
        note.append("## STEP 5 · LLM\n\n- skipped\n")
    else:
        print("  llm todos:")
        for t in suite["llm_todos"] or []:
            print(f"    [{'x' if t['done'] else ' '}] {t['title']}")
        assert len(suite["llm_todos"] or []) >= 3
        print("ASSERT: 模型写出 ≥3 条 todo → PASS")
        note.append("## STEP 5 · LLM todos\n")
        for t in suite["llm_todos"] or []:
            note.append(f"- {t}")
        note.append("")

    # ---- STEP 6 · 五维衔接 ----
    print("\n" + "=" * 52, "STEP 6 · 编排维落点")
    print("  编排维 += 显式 todos；信息流仍用 08.03 VFS read")
    print("  下一课：子 Agent 委派 + 长期记忆")
    note.append("## STEP 6\n\n- 编排：todos；信息流：VFS\n")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: deep_agents 验收通过")


if __name__ == "__main__":
    main()
