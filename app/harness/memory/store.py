# app/harness/memory/store.py
"""课次 08.05 · 最小 Memory Store：跨会话 put / get / search。

直觉：长期记忆像带锁的抽屉——按 key（常含 tenant/user）存偏好与结论。
演示默认进程内；可指向 json 文件做「第二次调用仍在」验收。
生产：换 Redis/DB，并强制租户隔离与审计。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


def _now() -> str:
    """统一时间格式：yyyy-MM-dd HH:mm:ss。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class MemoryRecord:
    """一条记忆。

    参数:
        key: 如 user:demo:pref / case:R-1:summary
        value: 明文（演示）；生产可加密
        tenant_id: 租户；get 时必须对上，防串租户
        source: 来源标记（user_explicit / system）——禁止写模型臆造
    """

    key: str
    value: str
    tenant_id: str = "demo"
    source: str = "user_explicit"
    updated_at: str = field(default_factory=_now)


class MemoryStore:
    """进程内记忆；可选持久化到 JSON 文件。

    生产注意:
        - key 必须带租户前缀或独立表按 tenant 过滤
        - 写入需可审计（本课用 audit 列表）
        - 读出给模型时标明「来自记忆」
    """

    def __init__(self, persist_path: Path | str | None = None) -> None:
        self._data: dict[str, MemoryRecord] = {}
        self.audit: list[dict[str, Any]] = []
        self.persist_path = Path(persist_path) if persist_path else None
        if self.persist_path and self.persist_path.exists():
            self._load()

    def _scoped(self, key: str, tenant_id: str) -> str:
        """内部存储键 = tenant + 业务 key，避免撞车。"""
        return f"{tenant_id}::{key}"

    def put(
        self,
        key: str,
        value: str,
        *,
        tenant_id: str = "demo",
        source: str = "user_explicit",
    ) -> str:
        """写入记忆。

        参数:
            key: 业务键
            value: 内容
            tenant_id: 租户
            source: 建议仅 user_explicit / confirmed；勿写幻觉

        返回:
            "ok"
        """
        if source not in {"user_explicit", "confirmed", "system"}:
            raise ValueError(f"拒绝来源 source={source!r}（防幻觉写记忆）")
        rec = MemoryRecord(
            key=key,
            value=value,
            tenant_id=tenant_id,
            source=source,
            updated_at=_now(),
        )
        self._data[self._scoped(key, tenant_id)] = rec
        self.audit.append(
            {
                "op": "put",
                "key": key,
                "tenant_id": tenant_id,
                "source": source,
                "at": rec.updated_at,
            }
        )
        self._save()
        return "ok"

    def get(self, key: str, *, tenant_id: str = "demo") -> str | None:
        """按租户读取；不存在返回 None。"""
        rec = self._data.get(self._scoped(key, tenant_id))
        self.audit.append(
            {
                "op": "get",
                "key": key,
                "tenant_id": tenant_id,
                "hit": rec is not None,
                "at": _now(),
            }
        )
        return None if rec is None else rec.value

    def search(self, query: str, *, tenant_id: str = "demo", limit: int = 8) -> list[dict[str, str]]:
        """简单子串搜索（同租户）。"""
        q = (query or "").strip()
        hits: list[dict[str, str]] = []
        if not q:
            return hits
        for rec in self._data.values():
            if rec.tenant_id != tenant_id:
                continue
            blob = f"{rec.key} {rec.value}"
            if q in blob or re.search(re.escape(q), blob, re.I):
                hits.append(
                    {
                        "key": rec.key,
                        "value": rec.value,
                        "source": rec.source,
                        "updated_at": rec.updated_at,
                    }
                )
            if len(hits) >= limit:
                break
        return hits

    def delete(self, key: str, *, tenant_id: str = "demo") -> bool:
        """删除一条记忆（偏好可编辑可删）。"""
        sk = self._scoped(key, tenant_id)
        existed = sk in self._data
        if existed:
            del self._data[sk]
            self.audit.append(
                {"op": "delete", "key": key, "tenant_id": tenant_id, "at": _now()}
            )
            self._save()
        return existed

    def _save(self) -> None:
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            sk: {
                "key": r.key,
                "value": r.value,
                "tenant_id": r.tenant_id,
                "source": r.source,
                "updated_at": r.updated_at,
            }
            for sk, r in self._data.items()
        }
        self.persist_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load(self) -> None:
        assert self.persist_path is not None
        raw = json.loads(self.persist_path.read_text(encoding="utf-8"))
        for sk, row in raw.items():
            self._data[sk] = MemoryRecord(
                key=row["key"],
                value=row["value"],
                tenant_id=row.get("tenant_id", "demo"),
                source=row.get("source", "user_explicit"),
                updated_at=row.get("updated_at") or _now(),
            )


# 默认进程内单例（演示）；跨进程请用 persist_path
DEFAULT_MEMORY = MemoryStore()
