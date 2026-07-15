# app/lessons/m06_04_single_agent.py
"""课次 06.04 · 单 Agent 落地：System + 两类 Tool + Loop + 会话记忆。

最小产品切片（智能客服）：
- 角色：拒编造、拒不可逆承诺
- 工具：业务状态类 get_inventory（可附 get_shipment）+ 知识类 search_knowledge
- 控制：max_steps；轨迹可返回前端验收
- 记忆：按 session_id 保留最近 N 轮，便于多轮补全 sku

默认离线脚本化也能验收三类话术；USE_CHAT=1 时走真模型 bind_tools。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.tools.inventory import get_inventory, get_shipment
from app.tools.knowledge import search_knowledge

# ---------------------------------------------------------------------------
# 可调开关
# ---------------------------------------------------------------------------

# 单次任务最多模型轮数（含 Final）
DEFAULT_MAX_STEPS = 6

# 每个会话最多保留多少条「用户/助手」消息（不含 system）
MAX_HISTORY_MESSAGES = 12

# Tool 类别标签：验收「≥2 类」时用
TOOL_CLASS: dict[str, str] = {
    "get_inventory": "业务状态",
    "get_shipment": "业务状态",
    "search_knowledge": "知识检索",
}

CUSTOMER_SYSTEM = (
    "你是电商只读客服助手。\n"
    "规则：\n"
    "1) 库存/是否有货 → 必须调用 get_inventory，禁止编造 stock 数字。\n"
    "2) 退货几天、运费、质保等政策 → 必须调用 search_knowledge，禁止瞎编条款。\n"
    "3) 运单到哪了 → 调用 get_shipment；没有运单号就追问，不要编 ETA。\n"
    "4) 综合问题可先后调多类工具，再用 Observation 汇总；不得与 Observation 矛盾。\n"
    "5) 与购物无关的闲聊/超出职责：礼貌拒答，不要假装查过库存。\n"
    "6) 不要承诺退款到账、改库、强制发货等不可逆操作。\n"
    "常见 SKU：EARPHONE-PRO-BK（黑）、EARPHONE-PRO-WH（白）、CABLE-USB-C。\n"
)

CUSTOMER_TOOLS = [get_inventory, search_knowledge, get_shipment]


@dataclass
class SessionState:
    """一个会话的短记忆：消息列表 + 已确认的 sku（结构化槽位）。"""

    messages: list[Any] = field(default_factory=list)
    sku: str = ""


class SessionStore:
    """进程内会话表（教学用；生产应换 Redis）。"""

    def __init__(self) -> None:
        self._data: dict[str, SessionState] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> SessionState:
        sid = (session_id or "default").strip() or "default"
        with self._lock:
            if sid not in self._data:
                self._data[sid] = SessionState()
            return self._data[sid]

    def clear(self, session_id: str) -> None:
        sid = (session_id or "default").strip() or "default"
        with self._lock:
            self._data.pop(sid, None)


# 模块级默认仓库（FastAPI 与 demo 共用）
SESSION_STORE = SessionStore()


def tool_classes_in_trace(trace: list[dict[str, Any]]) -> set[str]:
    """从轨迹里抽出工具「类别」集合（业务状态 / 知识检索）。"""
    classes: set[str] = set()
    for row in trace:
        name = row.get("tool") or row.get("action") or ""
        if name in TOOL_CLASS:
            classes.add(TOOL_CLASS[name])
    return classes


def _guess_sku(text: str, fallback: str = "") -> str:
    """从话术里抠常见 SKU 或「黑/白」别名。"""
    u = (text or "").upper()
    for key in ("EARPHONE-PRO-WH", "EARPHONE-PRO-BK", "CABLE-USB-C"):
        if key in u:
            return key
    if "白" in (text or ""):
        return "EARPHONE-PRO-WH"
    if "黑" in (text or "") or "pro" in (text or "").lower():
        return "EARPHONE-PRO-BK"
    return fallback


def _wants_inventory(text: str) -> bool:
    t = text or ""
    keys = ("货", "库存", "还有", "现货", "有没有", "多少件", "stock")
    return any(k in t.lower() if k.isascii() else k in t for k in keys)


def _wants_policy(text: str) -> bool:
    t = text or ""
    keys = ("退货", "退换", "运费", "质保", "保修", "几天", "政策", "无理由")
    return any(k in t for k in keys)


def _wants_shipment(text: str) -> bool:
    t = text or ""
    return "运单" in t or "物流" in t or "到哪" in t or "SF" in t.upper()


def _is_off_topic(text: str) -> bool:
    """明显无关：既不像库存/政策/运单，又像闲聊或越权。"""
    t = (text or "").strip()
    if not t:
        return True
    if _wants_inventory(t) or _wants_policy(t) or _wants_shipment(t):
        return False
    # 给个 sku 也算业务相关（多轮第二句可能只有货号）
    if _guess_sku(t):
        return False
    noise = ("天气", "讲笑话", "帮我写诗", "比特币", "今天星期")
    return any(k in t for k in noise) or (
        len(t) < 40 and not any(k in t for k in ("货", "单", "退", "保", "运"))
    )


def run_scripted_customer_turn(
    message: str,
    *,
    session: SessionState | None = None,
) -> dict[str, Any]:
    """离线脚本化客服：按意图选 Tool，保证三类验收话术可复现。"""
    session = session or SessionState()
    text = (message or "").strip()
    trace: list[dict[str, Any]] = []

    # 多轮：用户只报 sku 时先记住
    guessed = _guess_sku(text, session.sku)
    if guessed and ("sku" in text.lower() or "是" in text or guessed in text.upper()):
        session.sku = guessed

    if _is_off_topic(text) and not (_wants_inventory(text) or _wants_policy(text)):
        answer = (
            "这个问题超出只读客服范围（库存/运单/售后政策）。"
            "我没有查询业务系统。请换库存、退货政策或运单相关问题。"
        )
        session.messages.append(HumanMessage(content=text))
        session.messages.append(AIMessage(content=answer))
        return {
            "mode": "scripted",
            "reply": answer,
            "trace": trace,
            "tool_classes": set(),
            "session_sku": session.sku,
        }

    need_inv = _wants_inventory(text)
    need_policy = _wants_policy(text)
    need_ship = _wants_shipment(text)

    # 第二轮「还有货吗」：靠短记忆补 sku
    if need_inv or (session.sku and "货" in text):
        need_inv = True

    parts: list[str] = []

    if need_inv:
        sku = _guess_sku(text, session.sku) or "EARPHONE-PRO-BK"
        session.sku = sku
        obs = str(get_inventory.invoke({"sku": sku}))
        trace.append({"tool": "get_inventory", "args": {"sku": sku}, "observation": obs})
        if obs == "not_found":
            parts.append(f"库存查询：SKU {sku} 不在目录（not_found）。")
        elif "stock=0" in obs:
            parts.append(f"库存查询：{sku} 暂时无货（{obs}）。")
        else:
            parts.append(f"库存查询结果：{obs}（数字来自工具，非估算）。")

    if need_policy:
        obs = str(search_knowledge.invoke({"query": text}))
        trace.append(
            {"tool": "search_knowledge", "args": {"query": text}, "observation": obs}
        )
        if obs == "not_found":
            parts.append("政策检索：未命中相关条款，请改问退货/运费/质保。")
        else:
            parts.append(f"政策检索结果：{obs}")

    if need_ship:
        # 简易抠运单号
        tracking = "SF123456"
        for token in text.replace("，", " ").replace(",", " ").split():
            if token.upper().startswith(("SF", "YT")) and any(c.isdigit() for c in token):
                tracking = token.strip().upper()
                break
        obs = str(get_shipment.invoke({"tracking_no": tracking}))
        trace.append(
            {"tool": "get_shipment", "args": {"tracking_no": tracking}, "observation": obs}
        )
        parts.append(f"运单查询结果：{obs}")

    if not parts:
        if session.sku and not need_inv and not need_policy and not need_ship:
            answer = (
                f"已记住 sku={session.sku}。"
                "下一轮可以直接问「还有货吗」，我会用记忆里的编码查库存。"
            )
        else:
            answer = "请说明要查的库存 SKU、退货政策，或运单号；我可以调用对应工具查询。"
    else:
        answer = " ".join(parts) + " 以上均基于 Tool Observation，未编造业务状态。"

    session.messages.append(HumanMessage(content=text))
    session.messages.append(AIMessage(content=answer))
    # 裁剪历史
    if len(session.messages) > MAX_HISTORY_MESSAGES:
        session.messages = session.messages[-MAX_HISTORY_MESSAGES:]

    return {
        "mode": "scripted",
        "reply": answer,
        "trace": trace,
        "tool_classes": tool_classes_in_trace(trace),
        "session_sku": session.sku,
    }


def run_customer_agent_turn(
    message: str,
    *,
    session_id: str = "default",
    tenant_id: str = "demo",
    use_chat: bool | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    store: SessionStore | None = None,
) -> dict[str, Any]:
    """单轮客服入口（可多轮：同一 session_id 复用记忆）。

    参数:
        message: 用户本轮话术
        session_id: 会话 ID；对接前端 session
        tenant_id: 租户（本课仅回传，索引隔离留给 RAG 课）
        use_chat: None 时读环境变量 USE_CHAT
        max_steps: Loop 上限
        store: 可注入会话仓库（测用）

    返回:
        reply / trace / tool_classes / mode / session_id / tenant_id
    """
    store = store or SESSION_STORE
    session = store.get(session_id)
    if use_chat is None:
        use_chat = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}

    if not use_chat:
        out = run_scripted_customer_turn(message, session=session)
        return {
            **out,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "tool_classes": sorted(out["tool_classes"]),
            "steps": len(out["trace"]),
        }

    # ---- 真模型：把短历史拼进 question 旁白（简版记忆）----
    from app.models.factory import get_chat_model

    history_bits: list[str] = []
    if session.sku:
        history_bits.append(f"用户已确认 sku={session.sku}")
    for m in session.messages[-6:]:
        role = "用户" if isinstance(m, HumanMessage) else "助手"
        history_bits.append(f"{role}: {getattr(m, 'content', '')}")
    memo = "\n".join(history_bits)
    question = message if not memo else f"（会话摘要）\n{memo}\n\n（本轮）{message}"

    model = get_chat_model(temperature=0.1)
    # 临时换 System：复用 run_tool_agent 前，手工跑一轮带 CUSTOMER_SYSTEM
    result = _run_with_customer_system(
        question,
        model=model,
        max_steps=max_steps,
    )

    # 更新槽位与历史
    sku = _guess_sku(message, session.sku)
    if sku:
        session.sku = sku
    session.messages.append(HumanMessage(content=message))
    session.messages.append(AIMessage(content=result["answer"]))
    if len(session.messages) > MAX_HISTORY_MESSAGES:
        session.messages = session.messages[-MAX_HISTORY_MESSAGES:]

    classes = tool_classes_in_trace(result.get("trace") or [])
    return {
        "mode": "llm",
        "reply": result["answer"],
        "trace": result.get("trace") or [],
        "tool_classes": sorted(classes),
        "session_id": session_id,
        "tenant_id": tenant_id,
        "session_sku": session.sku,
        "steps": result.get("steps"),
    }


def _run_with_customer_system(question: str, *, model: Any, max_steps: int) -> dict[str, Any]:
    """在客服 System + 两类 Tool 上跑 Loop（基于 agent.run_tool_agent 同构逻辑）。"""
    # 直接调用 run_tool_agent 会用 AGENT_SYSTEM；这里用同结构自定义 messages
    from langchain_core.messages import ToolMessage

    tool_list = list(CUSTOMER_TOOLS)
    catalog = {t.name: t for t in tool_list}
    llm = model.bind_tools(tool_list)
    messages: list[Any] = [
        SystemMessage(content=CUSTOMER_SYSTEM),
        HumanMessage(content=question),
    ]
    trace: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        ai = llm.invoke(messages)
        messages.append(ai)
        tool_calls = getattr(ai, "tool_calls", None) or []
        if not tool_calls:
            return {
                "answer": str(ai.content or "").strip() or "(空回复)",
                "trace": trace,
                "steps": step,
            }
        for tc in tool_calls:
            name = tc.get("name") or ""
            args = tc.get("args") or {}
            tc_id = tc.get("id") or f"call_{step}_{name}"
            fn = catalog.get(name)
            if fn is None:
                obs = f"error: unknown tool {name!r}"
            else:
                try:
                    obs = str(fn.invoke(args))
                except Exception as exc:  # noqa: BLE001
                    obs = f"error: {type(exc).__name__}: {exc}"
            trace.append({"tool": name, "args": args, "observation": obs})
            messages.append(ToolMessage(content=obs, tool_call_id=tc_id))

    return {
        "answer": "已达最大步数仍未结束；请缩小问题或转人工。",
        "trace": trace,
        "steps": max_steps,
    }


# ---- 演示用三套固定话术 ----

DEMO_STOCK_ONLY = "黑色 Pro 耳机 EARPHONE-PRO-BK 还有多少件？"
DEMO_COMBO = "黑色 Pro 还有货吗？退货几天内可以？"
DEMO_OFF_TOPIC = "今天天气怎么样？顺便讲个笑话"
DEMO_TURN1_SKU = "我的 sku 是 EARPHONE-PRO-BK"
DEMO_TURN2_STOCK = "还有货吗？给准确数字。"


def demo_acceptance_suite(*, use_chat: bool = False) -> dict[str, Any]:
    """课堂三件套 + 多轮记忆，供脚本一次性验收。"""
    store = SessionStore()
    store.clear("s-stock")
    store.clear("s-combo")
    store.clear("s-off")
    store.clear("s-mem")

    stock = run_customer_agent_turn(
        DEMO_STOCK_ONLY, session_id="s-stock", use_chat=use_chat, store=store
    )
    combo = run_customer_agent_turn(
        DEMO_COMBO, session_id="s-combo", use_chat=use_chat, store=store
    )
    off = run_customer_agent_turn(
        DEMO_OFF_TOPIC, session_id="s-off", use_chat=use_chat, store=store
    )
    t1 = run_customer_agent_turn(
        DEMO_TURN1_SKU, session_id="s-mem", use_chat=use_chat, store=store
    )
    t2 = run_customer_agent_turn(
        DEMO_TURN2_STOCK, session_id="s-mem", use_chat=use_chat, store=store
    )
    return {
        "stock_only": stock,
        "combo": combo,
        "off_topic": off,
        "memory_turn1": t1,
        "memory_turn2": t2,
    }
