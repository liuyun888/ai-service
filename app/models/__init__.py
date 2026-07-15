# app/models 包：schemas（结构化合同）+ factory（多模型 Chat 工厂）
"""M05 起：Chat 模型统一从 factory.get_chat_model 拿，不要在业务里写死厂商 SDK。"""

from app.models.factory import get_chat_model, resolve_provider

__all__ = ["get_chat_model", "resolve_provider"]
