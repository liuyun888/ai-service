# scripts/smoke_extract.py
"""12.01 别名：python scripts/smoke_extract.py → 同 12_01_regex_llm_extract_demo。"""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("12_01_regex_llm_extract_demo.py")), run_name="__main__")
