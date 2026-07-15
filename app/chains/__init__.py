# app/chains/__init__.py
"""链式组装包。

- M03 问答链源码在 app/lessons/m03_02_qa_chain.py
- M05.01 起：LangChain LCEL 最小链在 hello_chain.py
"""

from app.chains.hello_chain import build_hello_chain, run_hello
from app.lessons.m03_02_qa_chain import augment, generate, run_rag

__all__ = ["augment", "generate", "run_rag", "build_hello_chain", "run_hello"]
