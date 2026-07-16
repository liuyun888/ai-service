# scripts/smoke_validate_retry.py
"""12.02 别名：python scripts/smoke_validate_retry.py。"""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).with_name("12_02_validate_retry_demo.py")),
    run_name="__main__",
)
