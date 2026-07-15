# app/harness/context/vfs.py
"""课次 08.03 · 虚拟文件系统（VFS）：按需 list / search / read。

直觉：别把图书馆搬进模型窗口；先给目录树，让 Agent 自己「抽一页」。
安全：根目录白名单 + 禁止穿越 + 拒绝 secrets 等敏感前缀。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# 可调：单次 read 默认最多吐多少字符（防一次读崩窗口）
DEFAULT_MAX_CHARS = 1200

# 相对路径前缀一旦匹配，一律拒绝（演示密钥目录）
DENIED_PREFIXES = ("secrets/", "secrets\\")


@dataclass(frozen=True)
class VFSConfig:
    """VFS 可调开关。

    参数:
        root: 知识根目录（绝对路径）
        max_chars: read 单次最大字符；改小更容易触发截断
    """

    root: Path
    max_chars: int = DEFAULT_MAX_CHARS


def default_knowledge_root(project_root: Path | None = None) -> Path:
    """默认知识库：ai-service/knowledge_base。

    参数:
        project_root: 项目根；None 时按本文件位置推到 ai-service/
    """
    base = project_root or Path(__file__).resolve().parents[3]
    return (base / "knowledge_base").resolve()


class VirtualFS:
    """可列目录、可检索、可读片段的文档树。

    所有对外路径都是相对 root 的 posix 风格字符串，例如 `manual/return_policy.md`。
    """

    def __init__(self, config: VFSConfig | None = None) -> None:
        if config is None:
            config = VFSConfig(root=default_knowledge_root())
        self.root = config.root.resolve()
        self.max_chars = int(config.max_chars)

    # ---- 安全解析 ----

    def _safe_resolve(self, rel: str) -> Path | str:
        """把相对路径解析到 root 内；失败返回 error= 字符串。

        返回:
            Path 成功；或以 error= 开头的说明（路径穿越 / 敏感目录）
        """
        raw = (rel or "").strip().lstrip("/")
        if not raw:
            return self.root
        # 统一成 posix，方便检查 secrets/
        norm = raw.replace("\\", "/")
        if any(norm == p.rstrip("/") or norm.startswith(p) for p in DENIED_PREFIXES):
            return "error=denied_prefix:secrets"
        # 禁止把绝对路径或奇怪盘符直接拼进来
        if Path(raw).is_absolute():
            return "error=absolute_path_not_allowed"
        target = (self.root / raw).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            return "error=path_outside_root"
        return target

    # ---- 对外能力 ----

    def list_docs(self, prefix: str = "") -> list[str]:
        """列出 prefix 下的文件（相对路径）。

        参数:
            prefix: 子目录，如 `manual`；空=整棵树

        返回:
            相对路径列表；若路径非法则单元素 error 列表
        """
        base = self._safe_resolve(prefix)
        if isinstance(base, str):
            return [base]
        if not base.exists():
            return []
        if base.is_file():
            return [str(base.relative_to(self.root).as_posix())]
        out: list[str] = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.root).as_posix()
            if any(rel == d.rstrip("/") or rel.startswith(d) for d in DENIED_PREFIXES):
                continue
            out.append(rel)
        return out

    def search_docs(self, query: str, *, limit: int = 8) -> list[dict[str, str]]:
        """在全文里找包含 query 的文件，返回路径 + 命中摘录。

        直觉：比 RAG 更「笨」的关键词搜索，足够演示按需加载。
        """
        q = (query or "").strip()
        if not q:
            return [{"path": "", "snippet": "error=empty_query"}]
        hits: list[dict[str, str]] = []
        for rel in self.list_docs(""):
            if rel.startswith("error="):
                continue
            text = (self.root / rel).read_text(encoding="utf-8")
            idx = text.find(q)
            if idx < 0:
                continue
            start = max(0, idx - 40)
            end = min(len(text), idx + len(q) + 80)
            snippet = text[start:end].replace("\n", " ")
            hits.append({"path": rel, "snippet": snippet})
            if len(hits) >= limit:
                break
        return hits

    def read_doc(
        self,
        path: str,
        *,
        offset: int = 0,
        limit: int | None = None,
        max_chars: int | None = None,
    ) -> str:
        """读取文件片段；默认最多 max_chars 字符。

        参数:
            path: 相对路径
            offset: 从第几个字符开始（0-based）
            limit: 最多读多少字符；None 则用 max_chars
            max_chars: 覆盖实例默认值

        返回:
            带路径头的文本，或 error=...
        """
        target = self._safe_resolve(path)
        if isinstance(target, str):
            return target
        if not target.exists() or not target.is_file():
            return f"error=not_found:{path}"
        text = target.read_text(encoding="utf-8")
        cap = int(max_chars if max_chars is not None else self.max_chars)
        span = int(limit if limit is not None else cap)
        span = max(0, min(span, cap))
        start = max(0, int(offset))
        chunk = text[start : start + span]
        truncated = start + span < len(text)
        header = f"[path={path} offset={start} len={len(chunk)} total={len(text)}]"
        body = chunk
        if truncated:
            body += "\n…[truncated; 可用更大 offset 继续 read]"
        return f"{header}\n{body}"

    def tree_summary(self, prefix: str = "") -> str:
        """给 System Prompt 用的短目录清单（不装正文）。"""
        files = self.list_docs(prefix)
        if not files:
            return "(空目录)"
        if files and files[0].startswith("error="):
            return files[0]
        return "\n".join(f"- {f}" for f in files)

    def stuff_all_chars(self, prefix: str = "manual") -> int:
        """统计「整包装进 Prompt」时手册字符数（对照用）。"""
        total = 0
        for rel in self.list_docs(prefix):
            if rel.startswith("error="):
                continue
            total += len((self.root / rel).read_text(encoding="utf-8"))
        return total


# 模块级默认实例，方便 Tool / Lesson 直接用
DEFAULT_VFS = VirtualFS()


def list_docs(prefix: str = "") -> list[str]:
    """封装：列出文档。"""
    return DEFAULT_VFS.list_docs(prefix)


def search_docs(query: str, limit: int = 8) -> list[dict[str, str]]:
    """封装：关键词搜索。"""
    return DEFAULT_VFS.search_docs(query, limit=limit)


def read_doc(
    path: str,
    offset: int = 0,
    limit: int | None = None,
    max_chars: int | None = None,
) -> str:
    """封装：按需读片段。"""
    return DEFAULT_VFS.read_doc(path, offset=offset, limit=limit, max_chars=max_chars)
