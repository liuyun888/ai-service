# scripts/smoke_extract_api.py
"""12.03 别名：python scripts/smoke_extract_api.py。"""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).with_name("12_03_ocr_orchestration_demo.py")),
    run_name="__main__",
)
