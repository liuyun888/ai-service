# scripts/08_03_context_engineering_demo.py
"""08.03 Context Engineering 演示。

【本课要感受的三件事】
1. 整本预装 Prompt 远大于「只给目录」
2. 轨迹里出现 list/search/read，回答引用真实路径
3. 路径穿越与 secrets 被拒；单次 read 有截断

工作目录：必须在 ai-service/ 下。
默认离线脚本化；USE_CHAT=1 时追加真模型轨迹。
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

from app.lessons.m08_03_context_engineering import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "context_engineering_result.md"


def main() -> None:
    use_chat = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
    print("=" * 52, "CONFIG")
    print("Context Engineering = 何时/以何粒度把什么放进窗口")
    print("ROOT =", ROOT)
    print("USE_CHAT =", int(use_chat), "| 默认脚本轨迹（不调 Chat）")

    suite = demo_suite(use_chat=use_chat)
    note: list[str] = [
        "# 08.03 Context Engineering · 实跑记录\n",
        "",
        f"- USE_CHAT={int(use_chat)}",
        f"- VFS root: `{suite['vfs_root']}`",
        f"- Tools: `{suite['tool_names']}`",
        "",
    ]

    # ---- STEP 1 · VFS 与 Tool ----
    print("\n" + "=" * 52, "STEP 1 · VFS 根目录与 Tool")
    print("  root:", suite["vfs_root"])
    print("  tools:", suite["tool_names"])
    assert set(suite["tool_names"]) >= {"list_docs", "search_docs", "read_doc"}
    assert Path(suite["vfs_root"]).is_dir()
    print("ASSERT: list/search/read 齐全 → PASS")
    note.append("## STEP 1 · Tools\n")
    note.append(f"- `{suite['tool_names']}`\n")

    # ---- STEP 2 · 预装 vs 目录 ----
    print("\n" + "=" * 52, "STEP 2 · 整本预装 vs 只给目录")
    b = suite["budget"]
    print(f"  Q: {b['question']}")
    print(f"  预装手册 Prompt ≈ {b['stuff_chars']} chars")
    print(f"  只给目录 Prompt ≈ {b['tree_chars']} chars")
    print(f"  节省 ≈ {b['saved_chars']} chars | 倍率 ≈ {b['ratio_stuff_over_tree']}x")
    print("  目录预览:\n" + "\n".join(f"    {ln}" for ln in b["tree_preview"].splitlines()[:8]))
    assert b["stuff_chars"] > b["tree_chars"] * 2
    assert b["manual_file_count"] >= 2
    print("ASSERT: 预装远大于目录树 → PASS")
    note.append("## STEP 2 · Prompt 预算\n")
    note.append(f"- stuff={b['stuff_chars']} tree={b['tree_chars']} ratio={b['ratio_stuff_over_tree']}x\n")

    # ---- STEP 3 · 脚本按需轨迹 ----
    print("\n" + "=" * 52, "STEP 3 · 按需轨迹（脚本）")
    s = suite["scripted"]
    print(f"  tools_used: {s['tools_used']}")
    for ev in s["trace"]:
        print(f"  - {ev['tool']}({ev['args']})")
    print(f"  reply: {s['reply'][:120]}")
    print(f"  cited: {s['cited_path']}")
    print(
        f"  startup_prompt≈{s['startup_prompt_chars']} | tool_payload≈{s['tool_payload_chars']}"
    )
    assert "list_docs" in s["tools_used"]
    assert "search_docs" in s["tools_used"] or "read_doc" in s["tools_used"]
    assert "read_doc" in s["tools_used"]
    assert "return_policy" in s["cited_path"]
    assert "不支持" in s["reply"] or "质量问题" in s["reply"]
    print("ASSERT: 轨迹含 list + read，回答引用路径 → PASS")
    note.append("## STEP 3 · 脚本轨迹\n")
    note.append(f"- tools: `{s['tools_used']}`")
    note.append(f"- reply: {s['reply']}")
    note.append(f"- cite: `{s['cited_path']}`\n")

    # ---- STEP 4 · 安全护栏 ----
    print("\n" + "=" * 52, "STEP 4 · 穿越 / secrets / 截断")
    safe = suite["safety"]
    print(f"  outside_blocked={safe['outside_blocked']} msg={safe['outside_msg']}")
    print(f"  secret_blocked={safe['secret_blocked']} msg={safe['secret_msg']}")
    print(f"  truncated_ok={safe['truncated_ok']} head={safe['read_sample_head']!r}")
    assert safe["outside_blocked"]
    assert safe["secret_blocked"]
    assert safe["truncated_ok"]
    print("ASSERT: 越界与 secrets 拒绝；read 可截断 → PASS")
    note.append("## STEP 4 · 安全\n")
    note.append(f"- outside: {safe['outside_msg']}")
    note.append(f"- secret: {safe['secret_msg']}")
    note.append(f"- truncate_ok: {safe['truncated_ok']}\n")

    # ---- STEP 5 · 可选真模型 ----
    print("\n" + "=" * 52, "STEP 5 · 真模型（可选）")
    if suite["llm"] is None:
        print("  跳过（USE_CHAT=0）。需要时: USE_CHAT=1 python scripts/08_03_context_engineering_demo.py")
        note.append("## STEP 5 · LLM\n\n- skipped (USE_CHAT=0)\n")
    else:
        llm = suite["llm"]
        print(f"  tools_used: {llm.get('tools_used')}")
        print(f"  reply: {(llm.get('reply') or '')[:160]}")
        used = set(llm.get("tools_used") or [])
        assert used & {"list_docs", "search_docs", "read_doc"}, llm
        print("ASSERT: 真模型调用了至少一种上下文工具 → PASS")
        note.append("## STEP 5 · LLM\n")
        note.append(f"- tools: `{llm.get('tools_used')}`")
        note.append(f"- reply: {llm.get('reply')}\n")

    # ---- STEP 6 · 与五维信息流衔接 ----
    print("\n" + "=" * 52, "STEP 6 · 信息流维落点")
    print("  信息流维 = 何时/以何粒度进窗口 → 本课 VFS + Tools")
    print("  下一刀：压缩与评估见 08.06；任务规划见 08.04")
    note.append("## STEP 6 · 五维映射\n")
    note.append("- 信息流：按需 read，不预装全书\n")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: context_engineering 验收通过")


if __name__ == "__main__":
    main()
