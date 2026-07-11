# app/prompts/loader.py
"""Prompt 模板加载器：读文件 → 填 {{变量}} → 得到最终字符串。

本课统一用 {{name}} 槽语法（与 compare.md / faq_few_shot.md 一致），
不引入 Jinja / LangChain，方便独立跑通。
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent

# 匹配 {{var_name}}；变量名只允许字母数字下划线
_SLOT_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def list_prompts() -> list[str]:
    """列出 prompts 目录下所有 .md 模板文件名（不含子目录）。"""
    return sorted(p.name for p in PROMPTS_DIR.glob("*.md"))


def load_raw(name: str) -> str:
    """只读模板原文，不做变量替换。

    :param name: 文件名，如 ``compare.md``（不要带路径）
    :raises FileNotFoundError: 文件不存在
    :raises ValueError: 名称含路径分隔符（防目录穿越）
    """
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"非法模板名：{name!r}，只允许纯文件名")
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"模板不存在：{path}")
    return path.read_text(encoding="utf-8")


def render(raw: str, mapping: dict[str, str], *, strict: bool = True) -> str:
    """把 ``{{key}}`` 替换为 mapping 中的值。

    :param raw: 模板原文
    :param mapping: 变量名 → 填充值
    :param strict: True 时若仍有未替换槽位则抛错；False 则原样保留
    :raises KeyError: strict 且存在未提供的变量
    """

    def _repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in mapping:
            if strict:
                raise KeyError(f"模板需要变量 {key!r}，但未传入")
            return m.group(0)
        return mapping[key]

    text = _SLOT_RE.sub(_repl, raw)
    if strict and "{{" in text:
        # 可能是写坏的槽（如 {{ 空格异常 }}）或未登记变量
        raise RuntimeError(f"渲染后仍含未替换片段：{text[text.index('{{') : text.index('{{') + 40]}")
    return text


def load_prompt(name: str, *, strict: bool = True, **vars: str) -> str:
    """读模板并填充变量，一步到位。

    无变量模板（如 system_assistant.md）直接 ``load_prompt("system_assistant.md")``。
    有变量时：``load_prompt("compare.md", context="...", role="导购", ...)``。
    """
    return render(load_raw(name), dict(vars), strict=strict)
