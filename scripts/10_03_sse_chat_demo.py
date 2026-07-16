# scripts/10_03_sse_chat_demo.py
"""10.03 ai-service SSE 直连接口演示。

【本课（service 侧）】
1. Content-Type = text/event-stream
2. 事件含 token… + done
3. 约定格式 data: {json}

工作目录：必须在 ai-service/ 下。
BFF 转发验收见 ai-bff/scripts/10_03_sse_forward_demo.py。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m10_03_sse_stream import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "sse_chat_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("ai-service SSE = /v1/chat/stream")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 10.03 ai-service SSE · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 1 · 事件约定")
    for row in suite["contract"]:
        print(f"  type={row['type']}: {row['meaning']}")
    assert {r["type"] for r in suite["contract"]} >= {"token", "done", "error"}
    print("ASSERT: token/done/error 约定齐全 → PASS")
    note.append("## 约定\n")
    for row in suite["contract"]:
        note.append(f"- `{row['type']}`: {row['meaning']}")
    note.append("")

    print("\n" + "=" * 52, "STEP 2 · TestClient 拉流")
    s = suite["stream"]
    print(f"  tokens={s['token_count']} has_done={s['has_done']}")
    print(f"  joined: {s['joined']}")
    print(f"  sample: {s['sample_line']}")
    assert s["token_count"] >= 3 and s["has_done"]
    assert "收到" in s["joined"]
    print("ASSERT: 增量 token + done → PASS")
    note.append("## 流\n")
    note.append(f"- joined: `{s['joined']}`")
    note.append(f"- types: `{s['event_types']}`\n")

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: sse_chat（ai-service）验收通过")


if __name__ == "__main__":
    main()
