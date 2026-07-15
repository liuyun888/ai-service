# app/chains/rag_chain.py
"""课次 05.06 · RAG Chain 组装：检索 → 闸门 → 填模板 → 生成。

零件来源：
- Retriever：05.05 KnowledgeRetriever
- 拒答闸门：04.01 同款心智（空命中 / top1 分过低 → 不调模型）
- 模型：05.02 get_chat_model
- 引用格式：延续 03.06 的 [n] (source=...) 编号

不修改 m03_02_qa_chain.py / m03_06_qa_chain.py（课件原文保持不动）。
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from app.chains.knowledge_retriever import KnowledgeRetriever
from app.lessons.m04_01_qa_chain import DEFAULT_MIN_SCORE, REFUSE_TEXT

# 链上 Prompt：只根据 context 答；不足要明说；文末列 source
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你只能根据【资料】回答用户问题。\n"
            "规则：\n"
            "1. 禁止编造资料里没有的数字、条款或承诺。\n"
            "2. 资料不足时明确说「根据现有资料无法确定」。\n"
            "3. 回答末尾用一行列出引用的 source（文件名即可）。\n\n"
            "【资料】\n{context}",
        ),
        ("human", "{question}"),
    ]
)


def format_docs(docs: list[Document]) -> str:
    """Document[] → Prompt 用的 context 字符串（带 [n] 与 source）。"""
    if not docs:
        return "（无检索结果）"
    lines: list[str] = []
    for i, d in enumerate(docs, start=1):
        src = (d.metadata or {}).get("source") or "unknown"
        lines.append(f"[{i}] (source={src}) {d.page_content}")
    return "\n".join(lines)


def _normalize_question(inputs: Any) -> str:
    """允许 chain.invoke("问题") 或 chain.invoke({"question": "..."})。"""
    if isinstance(inputs, str):
        q = inputs.strip()
    elif isinstance(inputs, dict):
        q = str(inputs.get("question") or inputs.get("query") or "").strip()
    else:
        raise TypeError(f"不支持的输入类型: {type(inputs)!r}")
    if not q:
        raise ValueError("question 不能为空")
    return q


def _top1_score(docs: list[Document]) -> float | None:
    if not docs:
        return None
    score = (docs[0].metadata or {}).get("score")
    if score is None:
        return None
    return float(score)


def should_refuse_docs(
    docs: list[Document],
    *,
    min_score: float = DEFAULT_MIN_SCORE,
) -> bool:
    """空命中或 top1 分过低 → 拒答（与 04.01 同款）。"""
    if not docs:
        return True
    top = _top1_score(docs)
    if top is None:
        # 没有 score 时：有文档仍放行（避免误杀），由 Prompt 约束
        return False
    return top < min_score


def build_rag_chain(
    retriever: KnowledgeRetriever,
    model: Runnable,
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    prompt: ChatPromptTemplate | None = None,
) -> Runnable:
    """组装可 invoke 的 RAG 链，返回 dict（含 answer / refused / sources…）。

    数据流：
      question
        → retriever → docs
        → 闸门（拒答则短路）
        → format_docs → prompt → model → str
    """
    tmpl = prompt or RAG_PROMPT
    gen = tmpl | model | StrOutputParser()

    def _run(inputs: Any) -> dict[str, Any]:
        question = _normalize_question(inputs)
        docs = retriever.invoke(question)
        top = _top1_score(docs)
        sources = [
            str((d.metadata or {}).get("source") or "")
            for d in docs
            if (d.metadata or {}).get("source")
        ]

        if should_refuse_docs(docs, min_score=min_score):
            reason = (
                "empty_hits"
                if not docs
                else f"top1_score={top} < min_score={min_score}"
            )
            return {
                "question": question,
                "answer": REFUSE_TEXT,
                "refused": True,
                "reason": reason,
                "top1_score": top,
                "min_score": min_score,
                "context": "",
                "sources": sources,
                "docs": docs,
            }

        context = format_docs(docs)
        answer = gen.invoke({"question": question, "context": context})
        return {
            "question": question,
            "answer": answer,
            "refused": False,
            "reason": "",
            "top1_score": top,
            "min_score": min_score,
            "context": context,
            "sources": sources,
            "docs": docs,
        }

    return RunnableLambda(_run)


def run_rag_chain(
    question: str,
    *,
    index: Any,
    top_k: int = 4,
    min_score: float = DEFAULT_MIN_SCORE,
    tenant_id: str = "",
    use_chat: bool = True,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """一键：索引 → Retriever →（可选真模型）整链 invoke。

    use_chat=False：仍检索+闸门；通过闸门时 answer 填「离线预览」+ context 摘要，不调 Chat。
    """
    retriever = KnowledgeRetriever(
        index=index,
        top_k=top_k,
        tenant_id=tenant_id,
    )

    if not use_chat:
        # 离线路径：复用闸门逻辑，跳过 Generate
        question_n = _normalize_question(question)
        docs = retriever.invoke(question_n)
        top = _top1_score(docs)
        sources = [
            str((d.metadata or {}).get("source") or "")
            for d in docs
            if (d.metadata or {}).get("source")
        ]
        if should_refuse_docs(docs, min_score=min_score):
            reason = (
                "empty_hits"
                if not docs
                else f"top1_score={top} < min_score={min_score}"
            )
            return {
                "question": question_n,
                "answer": REFUSE_TEXT,
                "refused": True,
                "reason": reason,
                "top1_score": top,
                "min_score": min_score,
                "context": "",
                "sources": sources,
                "docs": docs,
            }
        context = format_docs(docs)
        return {
            "question": question_n,
            "answer": f"(offline preview) 将根据以下资料生成作答：\n{context[:400]}",
            "refused": False,
            "reason": "",
            "top1_score": top,
            "min_score": min_score,
            "context": context,
            "sources": sources,
            "docs": docs,
        }

    from app.models.factory import get_chat_model

    chain = build_rag_chain(
        retriever,
        get_chat_model(temperature=temperature),
        min_score=min_score,
    )
    return chain.invoke({"question": question})
