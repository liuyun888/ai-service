# scripts/01_07_prompt_template_demo.py
"""Prompt 模板工程冒烟：加载 → 填变量 → 断言；可选再调真实模型。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.prompts.loader import list_prompts, load_prompt, load_raw, render

# —— False：只跑本地加载/渲染断言；True：再用渲染结果调一次真实模型 ——
USE_REAL_LLM = True

# FAQ 样例（填进 faq_few_shot.md 的 {{demos}}）
FAQ_DEMOS = """
示例1
Q: 周末下单何时发货？
A: 一般工作日 24 小时内发出；周末订单顺延到下一工作日处理。

示例2
Q: 能改送到公司吗？
A: 可以。请提供订单号与新地址，我帮你说明修改入口；我这边不能直接改库。

示例3
Q: 你们是不是明天肯定到？
A: 无法承诺「肯定」。通常时效以物流页面为准，你可以在订单里点「查看物流」查询。
""".strip()

# compare.md 最小槽位（本课只验证「能填满」，完整 CRISPE 见 01.03）
COMPARE_SLOTS = {
    "context": "用户通勤地铁 40 分钟，预算约 1000 元，对比两款降噪耳机。",
    "role": "数码导购助手",
    "insight": "优先匹配通勤降噪；缺参数写「未知」，禁止编造。",
    "statement": "给出推荐结论与 3 条对比要点。",
    "personality": "简洁、口语、不夸张营销。",
    "output_format": "用 Markdown：## 结论 / ## 对比 / ## 注意",
}

EXTRACT_SLOTS = {
    "schema_hint": (
        '{"order_id": string|null, "intent": "query_logistics"|"change_address"|"other", '
        '"need_human": boolean}'
    ),
    "user_text": "帮我查一下订单 ORD-10086 到哪了，急用。",
}


def smoke_system_assistant() -> str:
    """无变量模板：读出即用。"""
    text = load_prompt("system_assistant.md")
    assert "不知道" in text or "禁止" in text, "system_assistant.md 缺少安全边界句"
    print("=" * 40, "PASS system_assistant.md")
    print(text[:120].replace("\n", " "), "...")
    return text


def smoke_compare() -> str:
    """有变量模板：填满后不应再出现 {{。"""
    text = load_prompt("compare.md", **COMPARE_SLOTS)
    assert "{{" not in text, "compare.md 仍有未替换变量"
    assert "数码导购助手" in text
    print("=" * 40, "PASS compare.md")
    print(text[:160].replace("\n", " "), "...")
    return text


def smoke_faq() -> str:
    text = load_prompt(
        "faq_few_shot.md",
        demos=FAQ_DEMOS,
        question="今晚下单明天能到吗？",
    )
    assert "{{" not in text
    assert "今晚下单明天能到吗？" in text
    assert "无法承诺" in text  # 样例里应带上边界示范
    print("=" * 40, "PASS faq_few_shot.md")
    print(text[:160].replace("\n", " "), "...")
    return text


def smoke_extract() -> str:
    text = load_prompt("extract_json.md", **EXTRACT_SLOTS)
    assert "{{" not in text
    assert "ORD-10086" in text
    print("=" * 40, "PASS extract_json.md")
    print(text[:160].replace("\n", " "), "...")
    return text


def smoke_missing_var_raises() -> None:
    """故意少传变量，证明 strict 模式会报错（护栏，不是业务失败）。"""
    raw = load_raw("faq_few_shot.md")
    try:
        render(raw, {"question": "只传了一个槽"})
    except KeyError as e:
        print("=" * 40, "PASS 缺变量会 KeyError")
        print("捕获：", e)
        return
    raise AssertionError("期望 KeyError，却渲染成功了")


def optional_llm_call(prompt: str) -> str:
    from app.llm.client import call_chat

    return call_chat([{"role": "user", "content": prompt}], temperature=0.2)


def write_notes(parts: list[str]) -> Path:
    out = ROOT / "notes" / "prompt_template_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def main() -> None:
    names = list_prompts()
    print("prompts 目录模板：", names)
    assert "system_assistant.md" in names
    assert "compare.md" in names
    assert "faq_few_shot.md" in names
    assert "extract_json.md" in names

    rendered = {
        "system_assistant": smoke_system_assistant(),
        "compare": smoke_compare(),
        "faq_few_shot": smoke_faq(),
        "extract_json": smoke_extract(),
    }
    smoke_missing_var_raises()

    note_parts = [
        "# Prompt 模板工程记录\n",
        f"目录内模板：{', '.join(names)}\n",
    ]
    for key, text in rendered.items():
        note_parts.append(f"## {key}\n\n```text\n{text}\n```\n")

    if USE_REAL_LLM:
        print("\n>>> 真实模型：用 faq 渲染结果问一句")
        answer = optional_llm_call(rendered["faq_few_shot"])
        print("=" * 40, "LLM ANSWER")
        print(answer)
        note_parts.append(f"## llm_faq_answer\n\n{answer}\n")
    else:
        print("\n提示：本地加载/渲染已跑通。若要验真模型，设 USE_REAL_LLM = True 后重跑。")

    notes = write_notes(note_parts)
    print(f"\n记录已写入：{notes}")


# 若已安装 pytest，也可：pytest tests/test_prompt_loader.py -q
def test_loader_renders_three_templates() -> None:
    assert "禁止" in load_prompt("system_assistant.md") or "不知道" in load_prompt(
        "system_assistant.md"
    )
    assert "{{" not in load_prompt("compare.md", **COMPARE_SLOTS)
    assert "{{" not in load_prompt(
        "faq_few_shot.md", demos=FAQ_DEMOS, question="测试题？"
    )


def test_missing_slot_raises() -> None:
    try:
        load_prompt("faq_few_shot.md", question="缺 demos")
    except KeyError:
        return
    raise AssertionError("应抛 KeyError")


if __name__ == "__main__":
    main()
