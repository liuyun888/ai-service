# app/chains/knowledge_retriever.py
"""课次 05.05 · LangChain Retriever 适配器。

直觉（0 基础）：
- 专栏已有 retrieve() / retrieve_for_tenant()
- LangChain RAG 链只认：Retriever.invoke("问题") → list[Document]
- 本文件做「转接头」：内部仍调你原来的检索，对外吐 Document

不修改 m03_05_retriever.py（03.05 课件原文保持不动）。
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field, model_validator

from app.lessons.m03_05_retriever import retrieve as retrieve_legacy
from app.lessons.m04_03_tenant_store import TenantIndex, retrieve_for_tenant


class KnowledgeRetriever(BaseRetriever):
    """把专栏索引适配成标准 Retriever。

    参数：
        index: InMemoryIndex / MilvusIndex / TenantIndex
        top_k: 返回条数
        tenant_id: 使用 TenantIndex 时必填（空则沿用 04.03：直接报错）

    用法：
        r = KnowledgeRetriever(index=index, tenant_id="tenant_a", top_k=4)
        docs = r.invoke("七天无理由条件")
    """

    # 允许把自定义 index 对象放进 Pydantic 模型字段
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: Any
    top_k: int = Field(default=4, ge=1)
    tenant_id: str = Field(default="")

    @model_validator(mode="after")
    def _check_tenant_when_needed(self) -> KnowledgeRetriever:
        """TenantIndex 必须在构造时就能发现缺 tenant（安全默认）。

        真正抛错仍在检索时走 retrieve_for_tenant，这里只做可读性提示。
        """
        return self

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """实现 BaseRetriever 抽象方法：query → Document 列表。"""
        q = (query or "").strip()
        if not q:
            raise ValueError("query 不能为空")

        if isinstance(self.index, TenantIndex):
            # 04.03 安全行为：缺 tenant_id → ValueError，禁止查全库
            hits = retrieve_for_tenant(
                self.index,
                q,
                tenant_id=self.tenant_id,
                top_k=self.top_k,
            )
            return [
                Document(
                    page_content=chunk.text,
                    metadata={
                        "source": chunk.source,
                        "score": score,
                        "tenant_id": chunk.tenant_id,
                        "section": chunk.section,
                        "chunk_id": chunk.chunk_id,
                    },
                )
                for chunk, score in hits
            ]

        # 非租户索引：走 03.05 统一 retrieve（内存 / Milvus）
        raw_hits = retrieve_legacy(self.index, q, top_k=self.top_k)
        docs: list[Document] = []
        for chunk, score in raw_hits:
            docs.append(
                Document(
                    page_content=chunk.text,
                    metadata={
                        "source": chunk.source,
                        "score": score,
                        "section": getattr(chunk, "section", "") or "",
                        "chunk_id": getattr(chunk, "chunk_id", 0),
                    },
                )
            )
        return docs


def docs_preview(docs: list[Document], *, max_len: int = 64) -> list[str]:
    """打印友好的一行摘要（演示脚本用）。"""
    lines: list[str] = []
    for i, d in enumerate(docs, 1):
        meta = d.metadata or {}
        preview = d.page_content[:max_len].replace("\n", " ")
        if len(d.page_content) > max_len:
            preview += "…"
        score = meta.get("score")
        score_s = f"{float(score):.4f}" if score is not None else "?"
        tid = meta.get("tenant_id")
        tid_s = f" tenant={tid}" if tid else ""
        lines.append(
            f"#{i}  score={score_s}  source={meta.get('source', '')}{tid_s}  {preview}"
        )
    return lines
