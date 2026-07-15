# app/harness/skills/registry.py
"""课次 08.05 · 子 Agent Skill / brief 模板注册表。"""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent

# skill 名 → brief 文件
BRIEF_FILES = {
    "research_agent": SKILLS_DIR / "research_brief.md",
    "writer_agent": SKILLS_DIR / "writer_brief.md",
}


def load_brief(skill: str) -> str:
    """读取 brief 模板全文。

    参数:
        skill: research_agent / writer_agent

    返回:
        Markdown brief；不存在则抛 KeyError
    """
    path = BRIEF_FILES.get(skill)
    if path is None or not path.exists():
        raise KeyError(f"未知 skill 或缺失 brief: {skill}")
    return path.read_text(encoding="utf-8")


def list_skills() -> list[str]:
    """已注册的子 Agent 名。"""
    return sorted(BRIEF_FILES.keys())
