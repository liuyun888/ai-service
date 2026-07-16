# app/security/internal_auth.py
"""课次 10.04 · ai-service 只信「内部头」，不信前端随便传的租户。

直觉：BFF 已经验过用户 JWT；本服务只核对服务间共享密钥，
再读取 BFF 写入的 X-Tenant-Id / X-User-Id 等，用于隔离与路由。
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.config import INTERNAL_TOKEN


@dataclass(frozen=True)
class InternalContext:
    """一次受信任调用的上下文（来自 BFF 注入的头）。"""

    tenant_id: str
    user_id: str
    model_id: str
    request_id: str


def require_internal_context(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_model_id: str | None = Header(default=None, alias="X-Model-Id"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> InternalContext:
    """校验内部令牌 + 必填租户；缺一不可。

    抛出:
        HTTPException 401: 内部令牌不对或缺失
        HTTPException 400: 缺 X-Tenant-Id
    """
    expected = (INTERNAL_TOKEN or "").strip()
    got = (x_internal_token or "").strip()
    if not expected or got != expected:
        raise HTTPException(status_code=401, detail="unauthorized internal")

    tenant = (x_tenant_id or "").strip()
    if not tenant:
        raise HTTPException(status_code=400, detail="missing tenant")

    return InternalContext(
        tenant_id=tenant,
        user_id=(x_user_id or "").strip() or "unknown",
        model_id=(x_model_id or "").strip() or "default",
        request_id=(x_request_id or "").strip() or "-",
    )
