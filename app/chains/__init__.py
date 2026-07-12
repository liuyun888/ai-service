# app/chains/__init__.py
"""链式组装：把 RAG 在线后半段（Augment + Generate）串起来。"""

from app.chains.qa_chain import augment, generate, run_rag

__all__ = ["augment", "generate", "run_rag"]
