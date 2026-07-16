# app/ocr/mock_ocr.py
"""课次 12.03 · mock OCR：用固定样例模拟「影像 → 文本」。

真实项目把 mock_ocr 换成供应商 SDK 即可，下游抽取 API 不用改。
"""

from __future__ import annotations

from typing import Any

# 验收用：识别成功后的票据文本（字段齐全）
OCR_OK_TEXT = """
电子发票（普通发票）

发票号码：INV-2026-001
开票日期：2026-07-01
销售方名称：Acme 商贸
购买方名称：学员演示账号

价税合计（小写）：￥128.50
""".strip()

# 可调：文本短于该长度 → 编排侧判 need_human，不硬调抽取
MIN_TEXT_LEN = 10


def mock_ocr(image_id: str) -> dict[str, Any]:
    """按 image_id 返回模拟识别结果。

    约定 image_id（演示）：
      - img-1 / img-ok：成功，返回完整发票文本
      - img-empty：空文本（模拟识别失败）
      - img-short：过短文本
      - img-fail：显式失败（ok=False）
      - 其他未知 id：当作失败

    返回:
        ok, text, confidence(0~1), image_id, provider=mock
    """
    iid = (image_id or "").strip()
    if iid in ("img-1", "img-ok"):
        return {
            "ok": True,
            "text": OCR_OK_TEXT,
            "confidence": 0.92,
            "image_id": iid,
            "provider": "mock",
        }
    if iid == "img-empty":
        return {
            "ok": True,
            "text": "",
            "confidence": 0.1,
            "image_id": iid,
            "provider": "mock",
            "error": "empty_text",
        }
    if iid == "img-short":
        return {
            "ok": True,
            "text": "短",
            "confidence": 0.3,
            "image_id": iid,
            "provider": "mock",
        }
    if iid == "img-fail":
        return {
            "ok": False,
            "text": "",
            "confidence": 0.0,
            "image_id": iid,
            "provider": "mock",
            "error": "ocr_engine_error",
        }
    return {
        "ok": False,
        "text": "",
        "confidence": 0.0,
        "image_id": iid,
        "provider": "mock",
        "error": "unknown_image_id",
    }
