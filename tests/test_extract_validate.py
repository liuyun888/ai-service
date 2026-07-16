# tests/test_extract_validate.py
"""课次 12.02 / 13.02 · 抽取校验单测（CI / smoke 可跑）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.chains.extract_validate import validate_invoice


def test_valid_invoice() -> None:
    ok, data = validate_invoice(
        {
            "invoice_no": "INV-2026-001",
            "date": "2026-07-01",
            "amount": 12.0,
            "seller_name": "Acme",
        }
    )
    assert ok is True
    assert isinstance(data, dict)
    assert data["amount"] == 12.0


def test_reject_amount_with_unit() -> None:
    ok, err = validate_invoice(
        {
            "invoice_no": "INV-2026-001",
            "date": "2026-07-01",
            "amount": "12.00元",
            "seller_name": "Acme",
        }
    )
    assert ok is False
    assert "amount" in str(err)


def run_all() -> None:
    test_valid_invoice()
    test_reject_amount_with_unit()
    print("test_extract_validate: ALL PASS")


if __name__ == "__main__":
    run_all()
