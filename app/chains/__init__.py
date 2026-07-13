# app/chains/__init__.py
"""链式组装包。M03 问答链源码在 app/lessons/m03_02_qa_chain.py。"""

from app.lessons.m03_02_qa_chain import augment, generate, run_rag

__all__ = ["augment", "generate", "run_rag"]
