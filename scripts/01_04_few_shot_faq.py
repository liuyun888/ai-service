"""Zero-shot vs Few-shot 开关对比（OpenAI 兼容接口）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm.client import call_chat

# —— 对比开关：改 True / False 各跑一次，或直接跑 main 自动对比两档 ——
USE_FEW_SHOT = True

USER_Q = "今晚下单明天能到吗？"

# 步骤 1：三组成对样例（含一次「无法承诺」）
# 注意：样例在「教风格」——短句、先口径、不绝对承诺、不替用户改库
FEW_SHOT_DEMOS = """
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


def build_prompt(question: str, few_shot: bool) -> str:
    """按开关拼 Zero-shot 或 Few-shot Prompt。

    对比实验要点：两档共用同一句「弱」人设；
    Zero-shot 不再写「无法承诺」等细则，否则和 Few-shot 差异会被抹平。
    """
    # 故意写弱：只定身份，不定边界与句式（方便观察样例的作用）
    base = "你是电商售后助手，语气专业，尽量帮用户解答。"

    if not few_shot:
        # Zero-shot：只有模糊指令 + 新问题
        return f"{base}\n\n用户问：{question}\n请回答。"

    # Few-shot：同样弱指令 + 样例拉齐风格与边界
    return (
        f"{base}\n\n"
        f"下面有几组标准问答，请严格模仿其口吻、长度与边界"
        f"（尤其是不承诺绝对时效、不直接改库）：\n"
        f"{FEW_SHOT_DEMOS}\n\n"
        f"现在请用相同风格回答新问题（只答新问题，不要复述示例）：\n"
        f"Q: {question}"
    )


def run_once(few_shot: bool) -> tuple[str, str]:
    """调用一次模型，返回 (prompt, answer)。"""
    prompt = build_prompt(USER_Q, few_shot=few_shot)
    label = "few_shot" if few_shot else "zero_shot"
    print("=" * 40, label)
    print("PROMPT:\n", prompt)
    # temperature 略抬高，让 Zero-shot 更容易「自由发挥」，对比更明显
    answer = call_chat([{"role": "user", "content": prompt}], temperature=0.7)
    print("ANSWER:\n", answer)
    return prompt, answer


def main() -> None:
    # 自动跑两档，避免只改开关忘了对比
    results: list[str] = []
    for few_shot in (False, True):
        prompt, answer = run_once(few_shot)
        tag = "few_shot" if few_shot else "zero_shot"
        results.append(
            f"## {tag}\n\n"
            f"### Prompt\n\n```text\n{prompt}\n```\n\n"
            f"### Answer\n\n{answer}\n"
        )

    # 若只想跑开关当前值，可改为：run_once(USE_FEW_SHOT)
    _ = USE_FEW_SHOT  # 保留开关常量，便于你改成单次实验

    out = ROOT / "notes" / "few_shot_faq_compare.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"# Few-shot 对比\n\n用户问题：{USER_Q}\n\n" + "\n".join(results),
        encoding="utf-8",
    )
    print(f"\n已写入对比记录：{out}")


if __name__ == "__main__":
    main()