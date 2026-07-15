# app/harness/context/__init__.py
"""上下文装载与压缩（信息流维）。

- truncate.py：粗粒度字符截断示意（08.01）
- vfs.py：虚拟文件树 list/search/read（08.03）
- tools.py：LangChain Tool 封装（08.03）
"""

from app.harness.context.truncate import truncate_text
from app.harness.context.vfs import VirtualFS, default_knowledge_root, list_docs, read_doc, search_docs

__all__ = [
    "VirtualFS",
    "default_knowledge_root",
    "list_docs",
    "read_doc",
    "search_docs",
    "truncate_text",
]
