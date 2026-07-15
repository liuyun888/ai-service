# app/harness/middleware/compaction.py
"""课次 08.06 · Compaction：长对话压缩，不丢关键指针。

策略：
1. 保留全部 system（硬约束）
2. 保留最近 keep_recent 条 user/assistant（一轮≈2 条，默认约 4 轮）
3. 更早内容压成 summary，尽量保留路径/条款号指针
4. 超大 tool 输出改为 path 引用 + 短摘要
"""

from __future__ import annotations

import re
from typing import Any

# 可调：最近保留多少条非 system 消息（改小压缩更狠）
DEFAULT_KEEP_RECENT = 8

PATH_RE = re.compile(
    r"(manual/[\w\-./]+\.md|case/[\w\-./]+\.md|§\d+(?:\.\d+)?|path=[\w\-./]+)"
)


def _extract_pointers(messages: list[dict[str, str]]) -> list[str]:
    """从旧消息里捞路径/条款指针，写进摘要，避免只剩散文。"""
    found: list[str] = []
    for m in messages:
        for hit in PATH_RE.findall(m.get("content") or ""):
            if hit not in found:
                found.append(hit)
    return found[:12]


def compact_tool_payload(text: str, *, max_chars: int = 200, path_hint: str = "") -> str:
    """大工具输出 → 短摘要 + 可选路径指针。"""
    raw = text or ""
    if len(raw) <= max_chars:
        return raw
    ptr = path_hint or "（见原 Tool Observation / 文件路径）"
    head = raw[: max(0, max_chars - 40)].replace("\n", " ")
    return f"[tool_compact path={ptr}] {head}…"


def compact_messages(
    messages: list[dict[str, str]],
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
) -> dict[str, Any]:
    """压缩消息列表。

    参数:
        messages: [{role, content}, ...]
        keep_recent: 保留的最近非 system 条数

    返回:
        messages / before_chars / after_chars / summary / pointers
    """
    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    before = sum(len(m.get("content") or "") for m in messages)

    if len(rest) <= keep_recent:
        return {
            "messages": list(messages),
            "compacted": False,
            "before_chars": before,
            "after_chars": before,
            "summary": "",
            "pointers": _extract_pointers(rest),
            "dropped": 0,
        }

    old, recent = rest[:-keep_recent], rest[-keep_recent:]
    pointers = _extract_pointers(old)
    # 摘要：角色计数 + 指针，不复述闲聊全文
    summary = (
        f"【Compaction 摘要】较早 {len(old)} 条消息已压缩。"
        f"关键指针：{', '.join(pointers) if pointers else '（无显式路径）'}。"
        "详情请按路径 read，勿依赖本摘要全文。"
    )
    summary_msg = {"role": "system", "content": summary}
    out = [*system, summary_msg, *recent]
    after = sum(len(m.get("content") or "") for m in out)
    return {
        "messages": out,
        "compacted": True,
        "before_chars": before,
        "after_chars": after,
        "saved_chars": before - after,
        "summary": summary,
        "pointers": pointers,
        "dropped": len(old),
    }


def build_long_fake_dialog(*, turns: int = 20) -> list[dict[str, str]]:
    """造 N 轮假对话（含路径指针），供压缩演示。"""
    msgs: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "硬约束：不得绝对承诺到货；政策以 manual/return_policy.md 为准。",
        }
    ]
    for i in range(1, turns + 1):
        msgs.append({"role": "user", "content": f"第{i}轮：还要多久？补充闲聊……" * 3})
        ptr = "manual/return_policy.md" if i % 5 == 0 else "case/complaints_week.md"
        msgs.append(
            {
                "role": "assistant",
                "content": f"第{i}轮答复草稿……引用 {ptr} §2.1 ……" + ("冗余。" * 20),
            }
        )
    return msgs
