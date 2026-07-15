# scripts/06_03_loop_engineering_demo.py
"""06.03 Loop Engineering 演示。

【本课要感受的三件事】
1. 完整 Think → Act → Observe 轨迹可打印、可存笔记
2. max_steps 是刹车，不是玄学；用尽要兜底而非假成功
3. 重复调用检测能拦住「同一坏参数死磕」

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

from app.lessons.m06_03_loop_engineering import (  # noqa: E402
    DEFAULT_MAX_IDENTICAL,
    DEFAULT_MAX_STEPS,
    demo_duplicate_brake,
    demo_happy_path,
    demo_max_steps_brake,
    format_trace_lines,
)

NOTE_PATH = ROOT / "notes" / "loop_engineering_result.md"


def _print_trace(trace: list) -> None:
    for line in format_trace_lines(trace):
        print(" ", line)


def main() -> None:
    print("=" * 52, "CONFIG")
    print("本课以对照实验为主（默认不调 Chat）")
    print(f"DEFAULT_MAX_STEPS={DEFAULT_MAX_STEPS}, DEFAULT_MAX_IDENTICAL={DEFAULT_MAX_IDENTICAL}")
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    note: list[str] = [
        "# 06.03 Loop Engineering · 实跑记录\n",
        "",
        "## 循环骨架\n",
        "```text",
        "while not done and steps < max_steps:",
        "    Thought → (可选) Action → Observation → 写回上下文",
        "    或 Final Answer → done",
        "```",
        "",
        f"- 默认 `max_steps={DEFAULT_MAX_STEPS}`",
        f"- 默认重复检测阈值 `max_identical={DEFAULT_MAX_IDENTICAL}`",
        "",
    ]

    # ---- STEP 1 · 幸福路径：完整轨迹 ----
    print("\n" + "=" * 52, "STEP 1 · 幸福路径：两工具完整 TAO 轨迹")
    happy = demo_happy_path()
    _print_trace(happy["trace"])
    print("stop_reason:", happy["stop_reason"])
    print("answer:", happy["answer"])
    assert happy["stop_reason"] == "final"
    acts = [t for t in happy["trace"] if t.get("event") == "act"]
    assert len(acts) == 2
    assert acts[0]["action"] == "get_inventory"
    assert acts[1]["action"] == "get_shipment"
    assert "stock=12" in happy["answer"]
    print("ASSERT: 两工具 + final 退出 → PASS")
    note.append("## STEP 1 · 幸福路径轨迹\n")
    note.append("```text")
    note.extend(format_trace_lines(happy["trace"]))
    note.append("```")
    note.append(f"\n- stop_reason: `{happy['stop_reason']}`")
    note.append(f"- answer: {happy['answer']}\n")

    # ---- STEP 2 · 重复检测刹车 ----
    print("\n" + "=" * 52, "STEP 2 · 重复调用检测（同一坏 sku 死磕）")
    dup = demo_duplicate_brake(max_identical=2)
    _print_trace(dup["trace"])
    print("stop_reason:", dup["stop_reason"])
    print("answer:", dup["answer"])
    assert dup["stop_reason"] == "duplicate_stop"
    act_rows = [t for t in dup["trace"] if t.get("event") == "act"]
    assert len(act_rows) == 2  # 允许两次，第三次打断
    assert all(r["observation"] == "not_found" for r in act_rows)
    print("ASSERT: 连续相同调用被打断 → PASS")
    note.append("## STEP 2 · 重复检测\n")
    note.append("```text")
    note.extend(format_trace_lines(dup["trace"]))
    note.append("```")
    note.append(f"\n- stop_reason: `{dup['stop_reason']}`")
    note.append(f"- answer: {dup['answer']}\n")

    # ---- STEP 3 · max_steps 刹车 + 兜底 ----
    print("\n" + "=" * 52, "STEP 3 · max_steps 刹车与兜底话术")
    braked = demo_max_steps_brake(max_steps=3)
    _print_trace(braked["trace"])
    print("stop_reason:", braked["stop_reason"])
    print("answer preview:\n", braked["answer"][:280])
    assert braked["stop_reason"] == "max_steps"
    assert braked["steps"] == 3
    assert "步数已用尽" in braked["answer"]
    assert "转人工" in braked["answer"]
    print("ASSERT: 步数用尽给兜底、不假成功 → PASS")
    note.append("## STEP 3 · max_steps 兜底\n")
    note.append("```text")
    note.extend(format_trace_lines(braked["trace"]))
    note.append("```")
    note.append(f"\n- stop_reason: `{braked['stop_reason']}`")
    note.append(f"- answer:\n\n{braked['answer']}\n")

    # ---- STEP 4 · 旋钮小结（写进笔记当检查清单） ----
    print("\n" + "=" * 52, "STEP 4 · Loop 工程旋钮检查清单")
    checklist = [
        ("max_steps", "防止无限循环 / 账单爆炸", str(DEFAULT_MAX_STEPS)),
        ("重复调用检测", "相同 Tool+参数连打 → 打断", f"max_identical={DEFAULT_MAX_IDENTICAL}"),
        ("观察原样回灌", "not_found / error 字符串进轨迹", "见 STEP 1–2 observation 字段"),
        ("最终兜底", "步数用尽 → 事实清单 + 转人工", "见 STEP 3 answer"),
        ("轨迹一等公民", "每步 Thought/Action/Observation 可回放", "notes 里已落盘"),
    ]
    for name, why, where in checklist:
        print(f"  [{name}] {why} → {where}")
        assert name and why and where
    print("ASSERT: 五旋钮可对上演示 → PASS")
    note.append("## STEP 4 · 旋钮检查清单\n")
    note.append("| 旋钮 | 作用 | 本课落点 |")
    note.append("|------|------|----------|")
    for name, why, where in checklist:
        note.append(f"| {name} | {why} | {where} |")
    note.append("")

    note.append("## 结论\n")
    note.append("- Loop Engineering = 可约束 + 可观测 + 可停止，不是「再调大一点 max_steps」。")
    note.append("- 内循环 = 一次任务内的 Think/Act/Observe；外会话 = 多轮记忆（别混）。")
    note.append("- 分支多、要 HITL/持久化时再上 LangGraph（M07）；Loop 仍是图里的心脏。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: loop_engineering 验收通过")


if __name__ == "__main__":
    main()
