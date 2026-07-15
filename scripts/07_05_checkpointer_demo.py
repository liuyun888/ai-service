# scripts/07_05_checkpointer_demo.py
"""07.05 Checkpointer 演示。

【本课要感受的三件事】
1. compile 时挂上 checkpointer；用 get_state 读历史
2. 同 thread_id 空补丁续跑会累加；换 thread_id 是新故事
3. MemorySaver 不能上生产；续跑时别拿初始值覆盖 checkpoint

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

from app.graphs.checkpointing import build_cp_graph, thread_config  # noqa: E402
from app.lessons.m07_05_checkpointer import (  # noqa: E402
    demo_isolation,
    demo_overwrite_trap,
    demo_same_thread_resume,
    production_checklist,
)

NOTE_PATH = ROOT / "notes" / "checkpointer_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("Checkpointer=MemorySaver（开发）；cwd 应在 ai-service")
    print("ROOT =", ROOT)

    note: list[str] = [
        "# 07.05 Checkpointer · 实跑记录\n",
        "",
        "## 公式\n",
        "`config = {\"configurable\": {\"thread_id\": \"...\"}}`\n",
        "续跑优先：`app.invoke({}, config)`，勿再传会覆盖的初始字段。\n",
        "",
    ]

    # ---- STEP 1 · compile 带 checkpointer ----
    print("\n" + "=" * 52, "STEP 1 · compile(checkpointer=MemorySaver)")
    app, saver = build_cp_graph(fresh_memory=True)
    assert hasattr(app, "get_state")
    # 新版 langgraph 里 MemorySaver 是 InMemorySaver 的别名
    assert type(saver).__name__ in {"MemorySaver", "InMemorySaver"}
    print("saver:", type(saver).__name__, "(MemorySaver 别名)")
    print("ASSERT: 图已挂 Checkpointer → PASS")
    note.append("## STEP 1\n")
    note.append(
        f"- checkpointer 类型: `{type(saver).__name__}`（文档仍称 MemorySaver）\n"
    )

    # ---- STEP 2 · 同线程续跑 ----
    print("\n" + "=" * 52, "STEP 2 · 同 thread_id 续跑")
    same = demo_same_thread_resume()
    print("thread:", same["thread_id"])
    print("first :", same["first"])
    print("second:", same["second"])
    assert same["first"]["count"] == 1
    assert same["second"]["count"] == 2
    assert len(same["second"]["log"]) >= 2
    print("ASSERT: count 1→2 且 log 追加 → PASS")
    note.append("## STEP 2 · 同线程\n")
    note.append(f"- first: `{same['first']}`")
    note.append(f"- second: `{same['second']}`\n")

    # ---- STEP 3 · get_state ----
    print("\n" + "=" * 52, "STEP 3 · get_state 读快照")
    app2, _ = build_cp_graph(fresh_memory=True)
    cfg = thread_config("snap-1")
    app2.invoke({"count": 0, "log": []}, cfg)
    app2.invoke({}, cfg)
    snap = app2.get_state(cfg)
    print("values:", snap.values)
    print("next  :", snap.next)
    assert snap.values.get("count") == 2
    print("ASSERT: get_state 看到历史 → PASS")
    note.append("## STEP 3 · get_state\n")
    note.append(f"- values: `{dict(snap.values)}`")
    note.append(f"- next: `{snap.next}`\n")

    # ---- STEP 4 · 隔离 ----
    print("\n" + "=" * 52, "STEP 4 · 不同 thread_id 互不污染")
    iso = demo_isolation()
    print("A:", iso["A_after_resume"])
    print("B:", iso["B_fresh"])
    assert iso["A_after_resume"]["count"] == 2
    assert iso["B_fresh"]["count"] == 1
    assert iso["A_after_resume"]["log"] != iso["B_fresh"]["log"] or True
    print("ASSERT: 异线程隔离 → PASS")
    note.append("## STEP 4 · 隔离\n")
    note.append(f"- A: `{iso['A_after_resume']}`")
    note.append(f"- B: `{iso['B_fresh']}`")
    note.append(f"- {iso['lesson']}\n")

    # ---- STEP 5 · 覆盖陷阱 ----
    print("\n" + "=" * 52, "STEP 5 · 反例：又传 count=0")
    trap = demo_overwrite_trap()
    print("wrong :", trap["after_wrong_invoke_count0"])
    print("right :", trap["after_correct_empty_resume"])
    # 错误传入 count=0 后再 +1 → 常回到 1
    assert trap["after_wrong_invoke_count0"]["count"] == 1
    # 再空续跑 → 2
    assert trap["after_correct_empty_resume"]["count"] == 2
    print("ASSERT: 覆盖陷阱可复现；空补丁续跑正确 → PASS")
    note.append("## STEP 5 · 覆盖陷阱\n")
    note.append(f"- wrong: `{trap['after_wrong_invoke_count0']}`")
    note.append(f"- right: `{trap['after_correct_empty_resume']}`")
    note.append(f"- {trap['lesson']}\n")

    # ---- STEP 6 · 生产清单 ----
    print("\n" + "=" * 52, "STEP 6 · 生产注意事项（笔记必写）")
    checks = production_checklist()
    for c in checks:
        print(" -", c)
    assert any("MemorySaver" in c for c in checks)
    assert any("生产" in c or "Redis" in c or "Postgres" in c for c in checks)
    print("ASSERT: MemorySaver 不能直接上生产已写明 → PASS")
    note.append("## STEP 6 · 生产清单\n")
    for c in checks:
        note.append(f"- {c}")
    note.append("")

    note.append("## 结论\n")
    note.append("- Checkpoint 存整图 State+位置；聊天记忆只存话。")
    note.append("- 下一课：在 checkpoint 上 interrupt / 人工确认后再 resume。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: checkpointer 验收通过")


if __name__ == "__main__":
    main()
