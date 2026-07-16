# app/ops/cost.py
"""课次 13.02 · 成本粗算与调优杠杆清单。

数字仅供演示口感：真实账单以厂商 usage 为准。
迭代口诀：先 Harness / 数据 / 规则，最后才换更贵模型。
"""

from __future__ import annotations

from typing import Any

from app.harness.middleware.token_log import estimate_tokens

# 可调：演示单价（元 / 1K tokens）。改这里只影响笔记里的估算，不接真计费。
PRICE_PROMPT_PER_1K = 0.001
PRICE_COMPLETION_PER_1K = 0.002


def estimate_request_cost_cny(
    *,
    prompt: str,
    completion: str,
    prompt_price_per_1k: float = PRICE_PROMPT_PER_1K,
    completion_price_per_1k: float = PRICE_COMPLETION_PER_1K,
) -> dict[str, Any]:
    """根据文本粗估一轮请求的 token 与人民币成本。"""
    pt = estimate_tokens(prompt)
    ct = estimate_tokens(completion)
    cost = (pt / 1000.0) * prompt_price_per_1k + (ct / 1000.0) * completion_price_per_1k
    return {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": pt + ct,
        "est_cost_cny": round(cost, 6),
        "price_note": "演示单价，非厂商账单",
    }


def list_cost_levers() -> list[dict[str, str]]:
    """成本杠杆优先序（口述/笔记用）。"""
    return [
        {"order": "1", "lever": "规则/缓存", "why": "能规则或 FAQ 缓存解决的，不调模型"},
        {"order": "2", "lever": "检索 topK / 片段长度", "why": "少喂上下文 = 少花钱"},
        {"order": "3", "lever": "max_steps / 超时", "why": "Agent 空转是隐形账单"},
        {"order": "4", "lever": "模型分流", "why": "小模型路由，大模型只做难生成"},
        {"order": "5", "lever": "Compaction / 会话裁剪", "why": "长对话别整段回灌"},
        {"order": "6", "lever": "换更贵模型", "why": "最后手段；先证明 Harness/数据不够"},
    ]


def iteration_mantra() -> list[str]:
    """迭代口诀三行。"""
    return [
        "先 Harness（中间件、上下文、工具、图）",
        "再 数据（知识质量、切分、标注）",
        "后 模型（换供应商 / 微调）",
    ]
