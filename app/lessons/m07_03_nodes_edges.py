# app/lessons/m07_03_nodes_edges.py
"""课次 07.03 · 节点与边：三站流水线包装与职责说明。"""

from __future__ import annotations

from typing import Any

from app.graphs.pipeline import (
    USE_KNOWLEDGE_TOOL,
    analyze,
    build_pipeline,
    generate,
    retrieve,
    run_pipeline,
)


def node_responsibilities() -> list[dict[str, str]]:
    """每节点一句话职责（验收口述用）。"""
    return [
        {
            "node": "retrieve",
            "duty": "按 query 取 docs；空查询/失败写 error，不抛崩",
            "writes": "docs, error, path",
        },
        {
            "node": "analyze",
            "duty": "判断 docs 是否够用；写 summary 或 need_clarify",
            "writes": "summary, need_clarify, path",
        },
        {
            "node": "generate",
            "duty": "根据 summary / need_clarify 拼 answer",
            "writes": "answer, path",
        },
    ]


def demo_happy_path(query: str = "退货时效") -> dict[str, Any]:
    """主路径：有资料 → need_clarify=False → answer 含「基于资料」。"""
    out = run_pipeline(query)
    return {
        "query": query,
        "state": out,
        "use_knowledge_tool": USE_KNOWLEDGE_TOOL,
        "lesson": "边顺序固定：retrieve→analyze→generate",
    }


def demo_empty_docs(query: str = "今天月球天气如何") -> dict[str, Any]:
    """铺垫 07.04：检索空 → need_clarify=True，本课仍走到 generate。"""
    out = run_pipeline(query)
    return {
        "query": query,
        "state": out,
        "lesson": "分析可打标签；要不要改道留给条件边",
    }


def demo_partial_returns() -> dict[str, Any]:
    """证明节点只返回补丁：单独 invoke 函数看 keys。"""
    base: dict[str, Any] = {
        "query": "质保多久",
        "docs": [],
        "summary": "",
        "need_clarify": False,
        "answer": "",
        "path": [],
        "error": "",
    }
    r = retrieve(base)  # type: ignore[arg-type]
    mid = {**base, **r}
    a = analyze(mid)  # type: ignore[arg-type]
    mid2 = {**mid, **a}
    g = generate(mid2)  # type: ignore[arg-type]
    return {
        "retrieve_keys": sorted(r.keys()),
        "analyze_keys": sorted(a.keys()),
        "generate_keys": sorted(g.keys()),
        "final_answer": g.get("answer"),
        "path": (mid2.get("path") or []) + (g.get("path") or [])[-1:],
    }


def edge_topology() -> list[str]:
    """普通边列表（文档/笔记用）。"""
    return [
        "START → retrieve",
        "retrieve → analyze",
        "analyze → generate",
        "generate → END",
    ]


def compiled_ok() -> bool:
    app = build_pipeline()
    return hasattr(app, "invoke")
