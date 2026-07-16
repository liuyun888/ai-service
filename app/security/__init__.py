# app/security/__init__.py
"""服务端安全相关依赖（内部令牌、上下文）。"""

from app.security.internal_auth import InternalContext, require_internal_context

__all__ = ["InternalContext", "require_internal_context"]
