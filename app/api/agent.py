# app/api/agent.py
"""课次 05.07 + 06.04 · Tool Agent 与单 Agent HTTP 入口。

05.07（最小环）：
1. 模型能看到 Tool schema（bind_tools）
2. 若决定调用 → 执行函数 → 把 Observation 塞回 messages
3. 再让模型说 Final Answer
4. trace 里能看见调了哪个 tool、什么参数

06.04（落地）：
- POST /agent/chat：session 记忆 + 两类 Tool（库存/运单 + 知识检索）
- 开发期把 trace 返回，方便课堂验收「组合问 ≥2 类 Tool」
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

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


# ---------------------------------------------------------------------------
# 06.04 · HTTP：POST /agent/chat
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentChatRequest(BaseModel):
    """智能客服一问一答请求。

    需求点：C 端会话页 —— 用户发消息，后端跑单 Agent 再回包。
    """

    message: str = Field(..., min_length=1, description="用户本轮话术；对接：输入框内容")
    session_id: str = Field(
        "default",
        description="会话 ID，同会话可带短记忆；对接：前端生成的 session UUID",
    )
    tenant_id: str = Field(
        "demo",
        description="租户 ID；对接：登录态租户（本课仅回传，RAG 隔离见 M04）",
    )
    use_chat: bool | None = Field(
        None,
        description="是否走真模型；None=读环境变量 USE_CHAT；对接：调试开关",
    )


class AgentChatResponse(BaseModel):
    """客服回复 + 可选轨迹（课堂验收用）。"""

    reply: str = Field(..., description="助手最终回复；对接：聊天气泡")
    session_id: str
    tenant_id: str
    mode: str = Field(..., description="scripted | llm")
    trace: list[dict[str, Any]] = Field(default_factory=list, description="Tool 轨迹")
    tool_classes: list[str] = Field(
        default_factory=list,
        description="本轮用到的工具类别，如 业务状态/知识检索",
    )
    session_sku: str = Field("", description="会话里已记住的 sku（若有）")


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(body: AgentChatRequest) -> AgentChatResponse:
    """单 Agent 客服入口。

    需求点：智能客服页 / 课堂验收 —— 组合问题应出现 ≥2 类 Tool。
    """
    # 懒加载，避免与 lessons 互相 import 顶层环
    from app.lessons.m06_04_single_agent import run_customer_agent_turn

    out = run_customer_agent_turn(
        body.message,
        session_id=body.session_id,
        tenant_id=body.tenant_id,
        use_chat=body.use_chat,
    )
    return AgentChatResponse(
        reply=out["reply"],
        session_id=out["session_id"],
        tenant_id=out["tenant_id"],
        mode=out["mode"],
        trace=list(out.get("trace") or []),
        tool_classes=list(out.get("tool_classes") or []),
        session_sku=str(out.get("session_sku") or ""),
    )