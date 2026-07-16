# scripts/smoke_assistant.py
"""11.01 联调别名：等价于 11_01_assistant_integration_demo.py（正文点名）。"""

from __future__ import annotations

from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
runpy.run_path(str(HERE / "11_01_assistant_integration_demo.py"), run_name="__main__")
