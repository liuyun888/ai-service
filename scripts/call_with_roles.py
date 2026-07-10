# scripts/call_with_roles.py（优化后）
"""读取 System Prompt，与 User 分角色调用。"""

from __future__ import annotations

import sys
from pathlib import Path

# 保证从 scripts/ 运行时也能 import app.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm.client import call_chat


def main() -> None:
    system_path = ROOT / "app" / "prompts" / "system_assistant.md"
    if not system_path.exists():
        raise FileNotFoundError(f"请先创建 System 文件：{system_path}")

    system_text = system_path.read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": "请直接告诉我订单 ORD-999 的发货日期和快递单号"},
    ]
    # messages = [
    #     {"role": "system", "content": "你是乐于助人的助手。"},  # 故意不写禁止编造
    #     {
    #         "role": "user",
    #         "content": "禁止编造。请直接告诉我订单 ORD-999 的发货日期和快递单号。",
    #     },
    # ]
    print("即将发送的 messages：")
    for m in messages:
        preview = m["content"][:80].replace("\n", " ")
        print(f"  - role={m['role']}: {preview}...")

    answer = call_chat(messages)
    print("=" * 40)
    print("ANSWER:\n", answer)


if __name__ == "__main__":
    main()