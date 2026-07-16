"""结构化输出合同。

- 01.05 / 05.04：RecommendItem / RecommendResult（推荐列表）
- 12.02：InvoiceExtract（发票抽取校验；与 Prompt 解耦，便于单测）
"""

from __future__ import annotations

import re
from datetime import date as Date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


class InvoiceExtract(BaseModel):
    """课次 12.02 · 发票抽取结果合同（校验通过才能进表单/入库）。

    字段与 12.01 Schema 对齐：invoice_no / date / amount / seller_name。
    注意：字段名 date 与 datetime.date 冲突，注解用别名 Date。
    """

    invoice_no: str = Field(min_length=1, description="发票号码，非空")
    date: Date = Field(description="开票日期，须能解析为日期")
    amount: float = Field(ge=0, description="价税合计，数字且 ≥0")
    seller_name: Optional[str] = Field(default=None, description="销售方名称，可空")

    @field_validator("invoice_no")
    @classmethod
    def invoice_no_clean(cls, v: str) -> str:
        """号码去首尾空白；中间不许空格（防 OCR 脏数据混进）。"""
        v = (v or "").strip()
        if not v:
            raise ValueError("invoice_no 不能为空")
        if " " in v:
            raise ValueError("invoice_no 不应含空格")
        # 可调：只允许数字与短横线（演示用；真业务按税局规则收紧）
        if not re.fullmatch(r"[0-9A-Za-z-]+", v):
            raise ValueError("invoice_no 含非法字符")
        return v

    @field_validator("amount", mode="before")
    @classmethod
    def amount_must_be_number(cls, v: object) -> object:
        """拒绝「12.00元」「一百来块」这类字符串金额。

        不在这里偷偷 strip「元」——那会掩盖抽取质量问题；应回灌重试或人工。
        """
        if isinstance(v, bool):
            raise ValueError("amount 不能是布尔")
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            s = v.strip()
            # 纯数字字符串可以收（模型常吐 "1280.00"）
            if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", s):
                return float(s)
            raise ValueError("amount 须为数字，不要带单位或中文")
        return v
