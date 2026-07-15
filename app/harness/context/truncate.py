# app/harness/context/truncate.py
"""课次 08.01 · 上下文截断示意（横切能力放在 Harness，而不是每个 Agent 手写）。

生产会换成 token 计数 + 分层摘要；这里用字符长度让小白一眼看懂。
"""

from __future__ import annotations

# 可调：超过就截断并打标记。改小更容易触发截断。
DEFAULT_MAX_CHARS = 400


def truncate_text(text: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, object]:
    """截断过长文本；返回是否截断 + 结果。

    参数:
        text: 原始上下文字符串
        max_chars: 允许的最大字符数

    返回:
        {"text": 结果, "truncated": 是否截断, "original_len": 原长度}
    """
    raw = text or ""
    if len(raw) <= max_chars:
        return {"text": raw, "truncated": False, "original_len": len(raw)}
    cut = raw[: max(0, max_chars - 12)] + "…[truncated]"
    return {"text": cut, "truncated": True, "original_len": len(raw)}
