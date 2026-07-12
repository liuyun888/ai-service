# app/rag/__init__.py
"""RAG 离线/在线管道模块（M03）。

四步对应关系：
- Index 前半：splitters（切分）
- Index 后半：ingest（向量化 + 入库；本课先用内存索引，03.04 接 Milvus）
- Retrieve：retriever（按问题取 topK）
"""

from app.rag.ingest import InMemoryIndex, build_index
from app.rag.retriever import retrieve
from app.rag.splitters import Chunk, split_by_heading, split_fixed

__all__ = [
    "Chunk",
    "InMemoryIndex",
    "build_index",
    "retrieve",
    "split_by_heading",
    "split_fixed",
]
