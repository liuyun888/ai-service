"""把 compare.md 填成完整 CRISPE Prompt，并真实调用模型。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm.client import call_chat

# —— 六格取值（与上文表格一致）——
CONTEXT = """用户场景：每天地铁通勤 40 分钟，预算约 800～1200 元，更看重降噪与续航。

【耳机 A · 城际降噪 Pro】
- 主动降噪：有（厂商标注「通勤级」）
- 续航：降噪开约 28 小时
- 驱动单元：40mm
- 连接：蓝牙 5.2
- 参考价：999 元
- 未提供：通话降噪实测、重量

【耳机 B · 轻听 Air】
- 主动降噪：有（厂商标注「轻度降噪」）
- 续航：降噪开约 18 小时
- 驱动单元：30mm
- 连接：蓝牙 5.3
- 参考价：799 元
- 未提供：降噪深度分贝、是否支持多点连接
"""

SLOTS = {
    "context": CONTEXT.strip(),
    "role": "数码导购助手",
    "insight": (
        "优先匹配「通勤地铁降噪」；缺参数就写「未知」，禁止编造；"
        "价格只作参考，不承诺「最值」"
    ),
    "statement": "对比 A/B 两款耳机，给出推荐结论、3 条对比要点、1 条不适用人群",
    "personality": "简洁、口语、不夸张营销，单次回答控制在 300 字内",
    "output_format": (
        "必须用 Markdown 小标题：## 结论 / ## 对比 / ## 注意；"
        "对比用无序列表恰好 3 条"
    ),
}


def fill_template(template: str, slots: dict[str, str]) -> str:
    """用 {{key}} 占位符做简单替换（本课不引入 Jinja/LCEL）。"""
    text = template
    for key, value in slots.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise RuntimeError(f"模板仍有未替换变量，请检查 compare.md：{text[text.index('{{'):]}")
    return text


def main() -> None:
    template_path = ROOT / "app" / "prompts" / "compare.md"
    if not template_path.exists():
        raise FileNotFoundError(f"请先创建模板：{template_path}")

    template = template_path.read_text(encoding="utf-8")
    # 去掉文件头注释行，避免进 Prompt
    lines = [ln for ln in template.splitlines() if not ln.strip().startswith("<!--")]
    prompt = fill_template("\n".join(lines).strip(), SLOTS)

    print("=" * 40, "FINAL PROMPT")
    print(prompt)

    answer = call_chat([{"role": "user", "content": prompt}])
    print("=" * 40, "ANSWER")
    print(answer)

    out = ROOT / "notes" / "crispe_compare_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"## Final Prompt\n\n```text\n{prompt}\n```\n\n## Answer\n\n{answer}\n",
        encoding="utf-8",
    )
    print(f"\n已写入：{out}")


if __name__ == "__main__":
    main()