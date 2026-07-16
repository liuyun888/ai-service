# app/mcp/tools_search.py
"""课次 09.03 · 搜索知识库纯函数（复用 08.03 VFS；失败则友好 error=）。"""

from __future__ import annotations


def search_docs(query: str) -> str:
    """按关键词搜索知识库；不要用于写入或删改文件。

    参数:
        query: 非空关键词，如「已拆封」

    返回:
        多行 path :: snippet，或 error=...
    """
    q = (query or "").strip()
    if not q:
        return "error=empty_query; hint=传入关键词如 已拆封"
    try:
        from app.harness.context.vfs import DEFAULT_VFS

        hits = DEFAULT_VFS.search_docs(q, limit=5)
    except Exception as exc:  # noqa: BLE001
        return f"error=search_failed; hint={type(exc).__name__}: {exc}"
    if not hits:
        return f"error=no_hits; hint=换关键词或先 list 知识树; query={q!r}"
    lines = [f"{h['path']} :: {h['snippet'][:100]}" for h in hits]
    return "\n".join(lines)
