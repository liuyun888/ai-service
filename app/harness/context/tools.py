# app/harness/context/tools.py
"""课次 08.03 · 把 VFS 挂成 LangChain Tool（list / search / read）。

Agent 只拿目录 + 这些工具，不预装手册正文。
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.harness.context.vfs import DEFAULT_VFS, VirtualFS


def make_context_tools(vfs: VirtualFS | None = None) -> list[Any]:
    """生成绑定到指定 VFS 的 Tool 列表。

    参数:
        vfs: 虚拟文件系统；None 用默认 knowledge_base
    """
    fs = vfs or DEFAULT_VFS

    @tool
    def list_docs(prefix: str = "") -> str:
        """列出知识库文件路径。先 list 再 read，不要猜路径。

        参数:
            prefix: 子目录，如 manual 或 case；空表示整库
        """
        rows = fs.list_docs(prefix)
        return "\n".join(rows) if rows else "(empty)"

    @tool
    def search_docs(query: str) -> str:
        """在知识库全文关键词搜索，返回 path + 摘录。

        参数:
            query: 关键词，如「已拆封」「七天无理由」
        """
        hits = fs.search_docs(query)
        if not hits:
            return "no_hits"
        lines = [f"{h['path']} :: {h['snippet']}" for h in hits]
        return "\n".join(lines)

    @tool
    def read_doc(path: str, offset: int = 0, limit: int = 800) -> str:
        """按需读取文件片段；单次有长度上限。

        参数:
            path: 相对路径，如 manual/return_policy.md
            offset: 起始字符偏移
            limit: 本次最多读多少字符（仍受 VFS.max_chars 上限约束）
        """
        return fs.read_doc(path, offset=offset, limit=limit)

    return [list_docs, search_docs, read_doc]


# 默认 Tool 列表（绑 DEFAULT_VFS）
CONTEXT_TOOLS = make_context_tools()
