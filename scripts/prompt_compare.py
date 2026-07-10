"""同一用户问题，三档 Prompt 对比（OpenAI 兼容接口真实调用）。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from app.llm.client import call_chat, make_client

# 从 ai-service 根目录加载 .env（脚本在 scripts/ 下时也能找到）
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

USER_QUESTION = "我的退货什么时候能到账？"

PROMPTS = {
    "bad": "说说退货",
    "mid": "用客服语气说明退货到账时间",
    "good": (
        "你是电商售后助手。只根据下列政策回答，禁止编造具体天数。\n"
        "政策：审核通过后 3-7 个工作日原路退回；若未查到订单请说明无法确认。\n"
        "用不超过 5 条要点回答。\n"
        f"用户问题：{USER_QUESTION}"
    ),
}


def call_llm(client, prompt: str) -> str:
    return call_chat(
        [{"role": "user", "content": prompt}],
        client=client,
    )

def main() -> None:
    client = make_client()
    out_lines: list[str] = []
    for name, prompt in PROMPTS.items():
        print("=" * 40, name)
        print("PROMPT:\n", prompt)
        answer = call_llm(client, prompt)
        print("ANSWER:\n", answer)
        out_lines.append(f"## {name}\n\n### Prompt\n\n{prompt}\n\n### Answer\n\n{answer}\n")

    notes = Path(__file__).resolve().parents[1] / "notes" / "prompt_compare_result.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\n已写入对比记录：{notes}")


if __name__ == "__main__":
    main()