"""结构化输出合同：推荐列表（本课最小可用字段）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendItem(BaseModel):
    """单条推荐。"""

    name: str = Field(description="商品或方案名称")
    reason: str = Field(description="一句话理由")
    score: float = Field(ge=0, le=1, description="匹配度，0～1")


class RecommendResult(BaseModel):
    """推荐结果整体。"""

    items: list[RecommendItem]
    refuse: bool = False
    message: str = ""