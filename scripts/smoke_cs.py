# scripts/smoke_cs.py
"""11.02 联调别名：等价于 11_02_cs_integration_demo.py。"""

from __future__ import annotations

from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
runpy.run_path(str(HERE / "11_02_cs_integration_demo.py"), run_name="__main__")
