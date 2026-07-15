# app/chains/__init__.py
"""链式组装包。

- M03 问答链源码在 app/lessons/m03_02_qa_chain.py
- M05.01：LangChain LCEL 最小链 hello_chain.py
- M05.03：从 prompts/*.md 加载的 prompt_file_chain.py
- M05.04：parsers.py + recommend_chain.py（结构化输出）
- M05.05：knowledge_retriever.py（Retriever 适配器）
"""

from app.chains.hello_chain import build_hello_chain, run_hello
from app.chains.knowledge_retriever import KnowledgeRetriever
from app.chains.prompt_file_chain import build_assistant_chain, run_assistant
from app.chains.recommend_chain import build_recommend_chain, run_recommend
from app.lessons.m03_02_qa_chain import augment, generate, run_rag

__all__ = [
    "augment",
    "generate",
    "run_rag",
    "build_hello_chain",
    "run_hello",
    "build_assistant_chain",
    "run_assistant",
    "build_recommend_chain",
    "run_recommend",
    "KnowledgeRetriever",
]
