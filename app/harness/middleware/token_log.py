# app/harness/middleware/token_log.py
"""课次 08.06 · TokenLog 中间件（after_model）。

演示用字符粗估 token；生产接厂商 usage 字段。
"""

from __future__ import annotations

from typing import Any

# 可调：粗估比例。中文约 1.5～2 字/token；这里用 chars/2 够演示。
CHARS_PER_TOKEN = 2.0


def estimate_tokens(text: str) -> int:
    """用字符数粗估 token（非生产精度）。"""
    n = len(text or "")
    return max(0, int(round(n / CHARS_PER_TOKEN)))


def log_usage(
    trace_id: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, Any]:
    """记录本轮消耗，返回可写入 Trace 的事件。"""
    event = {
        "hook": "after_model",
        "middleware": "TokenLog",
        "trace_id": trace_id,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(prompt_tokens) + int(completion_tokens),
    }
    print(
        f"[TokenLog] trace={trace_id} prompt={prompt_tokens} "
        f"completion={completion_tokens} total={event['total_tokens']}"
    )
    return event


def log_usage_from_texts(
    trace_id: str,
    *,
    prompt: str,
    completion: str,
) -> dict[str, Any]:
    """根据文本粗估并记日志。"""
    return log_usage(
        trace_id,
        estimate_tokens(prompt),
        estimate_tokens(completion),
    )
