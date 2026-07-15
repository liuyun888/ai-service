# tests/test_harness.py
"""课次 08.06 · Harness 中间件单测：不测文采，测钩子是否触发。

用法（任选）：
  cd ai-service && python tests/test_harness.py
  # 若已装 pytest：pytest tests/test_harness.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.harness.middleware.compaction import compact_messages
from app.harness.middleware.guards import commitment_guard
from app.harness.middleware.redact import redact_pii


def test_commitment_guard_blocks() -> None:
    ok, out = commitment_guard("保证明天一定到货")
    assert ok is False
    assert "绝对承诺" in out


def test_commitment_guard_passes() -> None:
    ok, out = commitment_guard("当前物流显示已发货")
    assert ok is True
    assert "已发货" in out


def test_pii_redact() -> None:
    text = "手机 13800138000 证件 110101199001011234"
    out = redact_pii(text)
    assert "13800138000" not in out
    assert "110101199001011234" not in out
    assert "REDACTED" in out


def test_compaction_keeps_pointers() -> None:
    # 构造：很多旧消息带路径，keep_recent=4 应压缩且保留指针
    long = [
        {"role": "system", "content": "硬约束：看 manual/return_policy.md"},
    ]
    for i in range(12):
        long.append({"role": "user", "content": f"轮{i} 问……"})
        long.append(
            {"role": "assistant", "content": f"轮{i} 答 case/complaints_week.md §2.1"}
        )
    result = compact_messages(long, keep_recent=4)
    assert result["compacted"] is True
    assert result["after_chars"] < result["before_chars"]
    assert result["pointers"], "摘要应保留路径指针"
    assert any("硬约束" in (m.get("content") or "") for m in result["messages"])


def run_all() -> None:
    tests = [
        test_commitment_guard_blocks,
        test_commitment_guard_passes,
        test_pii_redact,
        test_compaction_keeps_pointers,
    ]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"SUMMARY: {len(tests)} tests ok")


if __name__ == "__main__":
    run_all()
