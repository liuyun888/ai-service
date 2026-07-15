# app/harness/__init__.py
"""生产 Harness：权限、护栏、HITL、可观测等（M06 起逐步填充）。

目录约定（08.01）：
- middleware/  调用前后钩子、安全门
- context/     上下文装载与压缩
- memory/      记忆挂钩
- skills/      Skill / 子任务约定
- shell.py     最小外壳对照（裸奔 vs 拴挽具）
"""