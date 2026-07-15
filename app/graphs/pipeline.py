# app/graphs/pipeline.py
"""课次 07.03 · 节点与边：检索 → 分析 → 生成 三站流水线。

边把步骤钉死（普通边，无条件路由——留给 07.04）：
  START → retrieve → analyze → generate → END

节点原则：
- 读 State，只 return 要变更的字段（PartialState）
- 副作用可有，但错误/空结果写回 State，不打崩进程
- mock 检索处标注「可替换为真实 Retriever / search_knowledge」
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

# 开关：True 时 retrieve 优先调 search_knowledge（仍属「可替换点」示意）
# 改 False → 纯假数据字符串，断网也能验收流水线形状
USE_KNOWLEDGE_TOOL = True


class PipelineState(TypedDict, total=False):
    """三站流水线共享状态。

    query: 用户问题
    docs: 检索到的片段列表（可为空）
    summary: 分析后的短摘要 / 标签
    need_clarify: 资料是否不够（为 07.04 条件边铺垫）
    answer: 最终给用户的话
    path: 走过的节点名（可观测）
    error: 可选错误信息
    """

    query: str
    docs: list[str]
    summary: str
    need_clarify: bool
    answer: str
    path: list[str]
    error: str


def _append_path(state: PipelineState, name: str) -> list[str]:
    """本课未上 reducer：每个节点带回完整 path。"""
    return list(state.get("path") or []) + [name]


def retrieve(state: PipelineState) -> dict[str, Any]:
    """站 1·检索：根据 query 写入 docs。

    【可替换】此处 mock / 可选 knowledge Tool；生产换成向量检索 Retriever。
    """
    query = (state.get("query") or "").strip()
    if not query:
        return {
            "docs": [],
            "error": "empty_query",
            "path": _append_path(state, "retrieve"),
        }

    docs: list[str] = []
    error = ""

    if USE_KNOWLEDGE_TOOL:
        # 可替换点：真实项目 → app.chains / Milvus retriever
        try:
            from app.tools.knowledge import search_knowledge

            obs = str(search_knowledge.invoke({"query": query}))
            if obs == "not_found":
                docs = []
            elif obs.startswith("error"):
                docs = []
                error = obs
            else:
                # 把「a | b」拆成多片段，模拟多 doc
                docs = [p.strip() for p in obs.split(" | ") if p.strip()]
        except Exception as exc:  # noqa: BLE001 — 写回 State，不炸图
            docs = []
            error = f"retrieve_failed: {type(exc).__name__}: {exc}"
    else:
        # 纯 mock：保证流水线形状可测
        docs = [f"[mock] 片段A about {query}", "[mock] 片段B 通用须知"]

    return {
        "docs": docs,
        "error": error,
        "path": _append_path(state, "retrieve"),
    }


def analyze(state: PipelineState) -> dict[str, Any]:
    """站 2·分析：判断资料够不够；够则写 summary，不够打 need_clarify。

    本课始终走向 generate（普通边）；澄清分支留给 07.04 条件边。
    """
    docs = list(state.get("docs") or [])
    if not docs:
        return {
            "summary": "",
            "need_clarify": True,
            "path": _append_path(state, "analyze"),
        }
    joined = " | ".join(docs)
    summary = joined[:200]
    return {
        "summary": summary,
        "need_clarify": False,
        "path": _append_path(state, "analyze"),
    }


def generate(state: PipelineState) -> dict[str, Any]:
    """站 3·生成：拼最终 answer（mock 模板，不调大模型）。"""
    if state.get("need_clarify"):
        answer = (
            "（资料不足）未能检索到相关片段。"
            "请补充更具体的问题（例如退货天数、运费规则），或转人工。"
        )
    else:
        summary = state.get("summary") or ""
        answer = f"基于资料：{summary}"
    return {
        "answer": answer,
        "path": _append_path(state, "generate"),
    }


def build_pipeline():
    """组装三节点图：普通边串成有向路径。"""
    g = StateGraph(PipelineState)
    g.add_node("retrieve", retrieve)
    g.add_node("analyze", analyze)
    g.add_node("generate", generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "analyze")
    g.add_edge("analyze", "generate")
    g.add_edge("generate", END)
    return g.compile()


def run_pipeline(query: str) -> PipelineState:
    """给演示脚本用的一键调用。"""
    app = build_pipeline()
    out = app.invoke(
        {
            "query": query,
            "docs": [],
            "summary": "",
            "need_clarify": False,
            "answer": "",
            "path": [],
            "error": "",
        }
    )
    return out  # type: ignore[return-value]


if __name__ == "__main__":
    print(run_pipeline("退货时效"))
