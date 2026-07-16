# app/ocr/__init__.py
"""OCR 上游适配（本专栏只做 mock 与接口契约，不讲识别算法）。"""

from app.ocr.mock_ocr import mock_ocr

__all__ = ["mock_ocr"]
