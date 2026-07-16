# scripts/smoke_kb_guard.py
"""11.04 联调别名：等价于 11_04_kb_guard_integration_demo.py。"""

from __future__ import annotations

from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
runpy.run_path(str(HERE / "11_04_kb_guard_integration_demo.py"), run_name="__main__")
