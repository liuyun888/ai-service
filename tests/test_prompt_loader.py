# tests/test_prompt_loader.py
"""Prompt 模板加载器单测（默认可本地跑，不调大模型）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.prompts.loader import load_prompt, list_prompts


COMPARE_SLOTS = {
    "context": "对比两款耳机。",
    "role": "导购",
    "insight": "不编造。",
    "statement": "给结论。",
    "personality": "简洁。",
    "output_format": "## 结论",
}


def test_prompts_dir_has_core_templates() -> None:
    names = list_prompts()
    for n in ("system_assistant.md", "compare.md", "faq_few_shot.md", "extract_json.md"):
        assert n in names, f"缺少模板：{n}"


def test_loader_renders_templates() -> None:
    sys_text = load_prompt("system_assistant.md")
    assert "不知道" in sys_text or "禁止" in sys_text

    compare = load_prompt("compare.md", **COMPARE_SLOTS)
    assert "{{" not in compare
    assert "导购" in compare

    faq = load_prompt(
        "faq_few_shot.md",
        demos="Q: a\nA: b",
        question="今晚能到吗？",
    )
    assert "{{" not in faq
    assert "今晚能到吗？" in faq


def test_missing_slot_raises() -> None:
    try:
        load_prompt("faq_few_shot.md", question="缺 demos")
    except KeyError:
        return
    raise AssertionError("应抛 KeyError")


if __name__ == "__main__":
    # 完整冒烟（含写笔记）走 scripts
    from scripts.prompt_template_demo import main

    main()
