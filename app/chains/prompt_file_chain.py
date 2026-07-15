# app/chains/prompt_file_chain.py
"""课次 05.03 · 从 prompts/*.md 加载提示词，接入 LCEL。

两条约定（本课刻意并存，别混用在同一段字符串里）：
1. LangChain ChatPromptTemplate：占位用单花括号 {question}
2. 本专栏 loader（01.07）：占位用双花括号 {{role}} —— 适合 compare.md 等 CRISPE

直觉：
- md 文件 = 可运营的「文案仓库」（改字不必改管道代码）
- ChatPromptTemplate = 链上的 Prompt 节，负责绑变量、产出 messages
- partial = 先填租户名等慢变量，调用时只传 question
"""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.prompts.loader import load_prompt, load_raw

# system 文案每次从 app/prompts 读盘（loader 已指向该目录），开发期改 md 立即生效


def load_system_text(name: str = "system_assistant.md") -> str:
    """每次从磁盘读 system 文案（开发期改 md 立刻生效，不缓存）。"""
    return load_raw(name)


def build_assistant_prompt(
    *,
    system_name: str = "system_assistant.md",
    tenant_name: str | None = None,
) -> ChatPromptTemplate:
    """system（文件）+ human（{question}）组成消息级模板。

    若传入 tenant_name，会 partial 进 system 末尾一行品牌约束，
    调用链时仍只传 question。
    """
    system = load_system_text(system_name)
    if tenant_name:
        # 慢变量预填：多租户时换品牌名不必动调用代码
        system = system.rstrip() + f"\n\n你当前服务的品牌是「{tenant_name}」。"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )
    if tenant_name:
        # 这里示范 partial 接口；tenant 已写进 system 字符串，
        # 若模板里还有 {tenant_name} 槽可改为 prompt.partial(tenant_name=...)
        return prompt
    return prompt


def build_assistant_chain(
    model: Runnable,
    *,
    system_name: str = "system_assistant.md",
    tenant_name: str | None = None,
) -> Runnable:
    """组装：文件模板 → 模型 → 字符串。"""
    prompt = build_assistant_prompt(system_name=system_name, tenant_name=tenant_name)
    return prompt | model | StrOutputParser()


def run_assistant(
    question: str,
    *,
    use_chat: bool = True,
    tenant_name: str | None = None,
    temperature: float = 0.2,
) -> str:
    """一键问答：system 来自 md，模型来自工厂（或离线）。"""
    from app.chains.hello_chain import make_offline_model
    from app.models.factory import get_chat_model

    model: Runnable = (
        get_chat_model(temperature=temperature) if use_chat else make_offline_model()
    )
    # 离线模型按「主题」句式工作；这里把 question 塞进可读 human 即可
    chain = build_assistant_chain(model, tenant_name=tenant_name)
    return chain.invoke({"question": question})


def build_compare_prompt(**crispe: str) -> ChatPromptTemplate:
    """先用 loader 填 compare.md 的 {{...}}，再整段当作 system 喂给 LC。

    为什么两步：
    - compare.md 沿用 01.07 的 {{var}}，loader 负责填 CRISPE
    - 填完后交给 ChatPromptTemplate，只留 {question} 给每轮用户问题
    """
    filled = load_prompt("compare.md", **crispe)
    # 若 filled 里碰巧含单个 { }，LC 会当变量；compare 正文我们控制过，一般没有
    return ChatPromptTemplate.from_messages(
        [
            ("system", filled),
            ("human", "{question}"),
        ]
    )


def run_compare(
    question: str,
    *,
    use_chat: bool = True,
    temperature: float = 0.2,
    **crispe: str,
) -> str:
    """导购对比：loader 填 CRISPE → LC 模板绑 question → 模型。"""
    from app.chains.hello_chain import make_offline_model
    from app.models.factory import get_chat_model

    defaults = {
        "context": "用户正在两款手机套餐之间犹豫。",
        "role": "电商导购",
        "insight": "只根据已知信息对比，缺数据就说明缺什么，不编造。",
        "statement": "用条目对比两款方案的差异，并给一句可执行建议。",
        "personality": "耐心、口语、不施压。",
        "output_format": "先列对比点，再给一句推荐理由；不要编造价格数字。",
    }
    defaults.update(crispe)

    model: Runnable = (
        get_chat_model(temperature=temperature) if use_chat else make_offline_model()
    )
    chain = build_compare_prompt(**defaults) | model | StrOutputParser()
    return chain.invoke({"question": question})


def preview_messages(prompt: ChatPromptTemplate, variables: dict[str, Any]) -> list[str]:
    """调试用：看模板绑完变量后的 messages 文本（不调模型）。"""
    value = prompt.invoke(variables)
    lines: list[str] = []
    for m in value.to_messages():
        content = str(m.content)
        preview = content if len(content) <= 240 else content[:240] + "…"
        lines.append(f"[{m.type}] {preview}")
    return lines
