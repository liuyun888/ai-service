# app/api/agent.py
"""课次 05.07 · 最小 Tool-calling / ReAct 初体验。

不做完整 Loop 工程（留给 M06）：这里只要：
1. 模型能看到 Tool schema（bind_tools）
2. 若决定调用 → 执行函数 → 把 Observation 塞回 messages
3. 再让模型说 Final Answer
4. trace 里能看见调了哪个 tool、什么参数

可选：USE_CHAT=0 时用「脚本化一步 ReAct」不调模型，也能验收 Tool 本身。
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.tools.inventory import get_inventory, get_shipment

# 默认挂上的只读工具（可按场景裁剪）
DEFAULT_TOOLS: list[BaseTool] = [get_inventory, get_shipment]

AGENT_SYSTEM = (
    "你是只读业务助手。涉及库存、运单等实时事实时，必须调用工具查询，禁止编造数字。\n"
    "已知常见 SKU：EARPHONE-PRO-BK（黑）、EARPHONE-PRO-WH（白）、CABLE-USB-C。\n"
    "查到 not_found 就如实告知；查到 stock=0 要说明暂时无货。\n"
    "不要承诺下单、改库、退款。"
)


def _tools_by_name(tools: list[BaseTool]) -> dict[str, BaseTool]:
    return {t.name: t for t in tools}


def run_scripted_inventory_demo(sku: str = "EARPHONE-PRO-BK") -> dict[str, Any]:
    """离线一步「伪 ReAct」：固定 Thought → Action → Observation → Answer。

    不调大模型，专门验收 Tool 可独立 invoke，并让你看见循环形态。
    """
    key = sku.strip().upper()
    thought = f"用户问库存，应调用 get_inventory，sku={key}"
    observation = get_inventory.invoke({"sku": key})
    trace = [{"tool": "get_inventory", "args": {"sku": key}, "observation": observation}]
    if observation == "not_found":
        answer = f"查过了：SKU {key} 不在目录里（not_found）。"
    elif "stock=0" in observation:
        answer = f"查过了：{key} 目前库存为 0，暂时无货。"
    else:
        answer = f"查过了：{observation}。以上数字来自库存工具，不是估算。"
    return {
        "mode": "scripted",
        "thought": thought,
        "answer": answer,
        "trace": trace,
        "steps": 1,
    }


def run_tool_agent(
    question: str,
    *,
    model: BaseChatModel,
    tools: list[BaseTool] | None = None,
    max_steps: int = 4,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """最小工具循环（ReAct 初体验）。

    参数:
        question: 用户问题
        model: 已能 chat 的模型（建议 05.02 get_chat_model）
        tools: 工具列表，默认库存+运单
        max_steps: 最多「模型回复」轮数（含最终回答那一轮）
        on_step: 每步回调，方便演示脚本打印日志

    返回:
        answer / trace / steps / messages（messages 便于调试）
    """
    tool_list = list(tools or DEFAULT_TOOLS)
    catalog = _tools_by_name(tool_list)
    llm = model.bind_tools(tool_list)

    messages: list[Any] = [
        SystemMessage(content=AGENT_SYSTEM),
        HumanMessage(content=question),
    ]
    trace: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        ai: AIMessage = llm.invoke(messages)  # type: ignore[assignment]
        messages.append(ai)
        tool_calls = getattr(ai, "tool_calls", None) or []

        if on_step:
            on_step(
                {
                    "step": step,
                    "has_tool_calls": bool(tool_calls),
                    "content_preview": str(ai.content or "")[:160],
                    "tool_calls": tool_calls,
                }
            )

        if not tool_calls:
            # 没有工具调用 = 认为给出 Final Answer
            return {
                "mode": "llm",
                "answer": str(ai.content or "").strip() or "(空回复)",
                "trace": trace,
                "steps": step,
                "messages": messages,
            }

        # Thought（隐式）→ Action：逐个执行 Tool，Observation 写回
        for tc in tool_calls:
            name = tc.get("name") or ""
            args = tc.get("args") or {}
            tc_id = tc.get("id") or f"call_{step}_{name}"
            tool_fn = catalog.get(name)
            if tool_fn is None:
                obs = f"error: unknown tool {name!r}"
            else:
                try:
                    obs = str(tool_fn.invoke(args))
                except Exception as exc:  # noqa: BLE001 — 返回给模型可读错误
                    obs = f"error: {type(exc).__name__}: {exc}"
            trace.append({"tool": name, "args": args, "observation": obs})
            messages.append(ToolMessage(content=obs, tool_call_id=tc_id))

    return {
        "mode": "llm",
        "answer": "已达最大步数仍未结束；请缩小问题或提高 max_steps。",
        "trace": trace,
        "steps": max_steps,
        "messages": messages,
    }


def build_default_agent_runner(*, use_chat: bool = True):
    """给演示脚本用的薄封装：离线脚本化 / 真模型工具环。"""

    def _run(question: str) -> dict[str, Any]:
        if not use_chat:
            # 离线：从问题里抠一个常见 SKU，否则默认黑色耳机
            sku = "EARPHONE-PRO-BK"
            for key in ("EARPHONE-PRO-WH", "EARPHONE-PRO-BK", "CABLE-USB-C"):
                if key in question.upper() or (
                    "白" in question and "WH" in key
                ):
                    sku = key
                    break
            if "白" in question:
                sku = "EARPHONE-PRO-WH"
            return run_scripted_inventory_demo(sku)

        from app.models.factory import get_chat_model

        return run_tool_agent(question, model=get_chat_model(temperature=0.1))

    return _run
