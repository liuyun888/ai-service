# app/lessons/m06_01_agent_vs_chat.py
"""课次 06.01 · Chat vs Agent：同一问题两种行为模式。

心智公式（本课必须记住）：
  Agent ≈ Model + Tools + 控制策略（Loop）

对照实验：
- Chat：不绑 Tool，一次生成 → 容易「猜」库存数字
- Agent：bind_tools + 最多 N 步 → 数字来自 Observation

不修改 05.07 的 Tool 定义；复用 app.api.agent / app.tools.inventory。
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.api.agent import run_scripted_inventory_demo, run_tool_agent
from app.tools.inventory import MOCK_CATALOG, get_inventory

# Chat 侧故意不给「必须查工具」硬约束，模拟「只会聊天」的助手
CHAT_ONLY_SYSTEM = (
    "你是热情的电商客服。用户问库存时，请直接给出听起来合理的数字和结论。"
    "不必声称查过系统。（本演示用于对比 Agent，刻意不加工具。）"
)

# 笔记三列：示例答案（动手时鼓励同学改成自己的）
NOTE_THREE_COLUMNS_EXAMPLE = {
    "chat_ok": [
        "解释「七天无理由」政策条文（资料已在 Prompt/RAG 里）",
        "润色一段已有话术",
        "把 JSON 字段翻译成人话（字段已给定）",
    ],
    "agent_needed": [
        "查实时库存/运单/号源（真相在业务 API）",
        "先查订单再查物流再汇总（多步）",
        "检索政策 + 再查系统状态组合回答",
    ],
    "should_not_auto": [
        "不可逆转账/退款（需 HITL）",
        "直接改库、强制发货",
        "医疗诊断结论、法律责任承诺",
    ],
}


def run_chat_only(
    question: str,
    *,
    model: BaseChatModel,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """纯 Chat：不 bind_tools，一次 invoke 结束。

    返回里 trace 恒为空——这是和 Agent 最刺眼的差异。
    """
    # 有的封装 get_chat_model 已带 temperature；此处再 invoke 时用 messages 即可
    ai = model.invoke(
        [
            SystemMessage(content=CHAT_ONLY_SYSTEM),
            HumanMessage(content=question),
        ]
    )
    text = str(getattr(ai, "content", ai) or "").strip()
    return {
        "mode": "chat_only",
        "answer": text or "(空回复)",
        "trace": [],
        "steps": 1,
        "used_tools": False,
    }


def run_chat_only_offline(question: str) -> dict[str, Any]:
    """离线假 Chat：模仿「没查系统就给数字」的回答（不调模型）。"""
    # 故意写一个和真实 MOCK 不同的数字，方便对照
    fake = (
        f"（离线假 Chat）关于「{question[:40]}…」："
        "黑色耳机热销款一般还有大概 3～5 件吧，建议尽快下单。"
        "【注意：此数字未查库存系统，仅演示幻觉风险】"
    )
    return {
        "mode": "chat_only_offline",
        "answer": fake,
        "trace": [],
        "steps": 1,
        "used_tools": False,
    }


def run_agent_side(
    question: str,
    *,
    model: BaseChatModel | None,
    use_chat: bool,
) -> dict[str, Any]:
    """Agent 侧：离线脚本化 或 真工具循环。"""
    if not use_chat or model is None:
        # 从问题里尽量识别 SKU
        sku = "EARPHONE-PRO-BK"
        upper = question.upper()
        for key in MOCK_CATALOG:
            if key in upper:
                sku = key
                break
        if "白" in question:
            sku = "EARPHONE-PRO-WH"
        out = run_scripted_inventory_demo(sku)
        out["used_tools"] = True
        return out

    out = run_tool_agent(
        question,
        model=model,
        tools=[get_inventory],
        max_steps=4,
    )
    out["used_tools"] = bool(out.get("trace"))
    return out


def label_parts_for_05_07() -> dict[str, str]:
    """回顾 05.07：标出三件套分别落在哪。"""
    return {
        "Model": "get_chat_model() / bind_tools 后的大模型",
        "Tools": "get_inventory / get_shipment（@tool）",
        "控制策略(Loop)": "run_tool_agent 里 max_steps +「有 tool_calls 就执行再问、没有就停」",
    }


def ground_truth_stock(sku: str = "EARPHONE-PRO-BK") -> str:
    """真实 mock 库存（对照 Chat 是否编数）。"""
    return get_inventory.invoke({"sku": sku})
