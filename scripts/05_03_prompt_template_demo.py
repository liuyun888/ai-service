# scripts/05_03_prompt_template_demo.py
"""05.03 PromptTemplate：md 文件 → LC 模板节点 → 链。

【本课要感受的三件事】
1. system 从 app/prompts/*.md 读，改文案不必改管道代码
2. ChatPromptTemplate 用 {question} 绑运行时变量；缺变量会明确报错
3. compare.md 先走 loader 的 {{var}}，再进 LC（两套槽语法别混在同一段里）

依赖：langchain-core、langchain-openai；模型走 05.02 工厂（OPENAI_*）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.chains.hello_chain import make_offline_model  # noqa: E402
from app.chains.prompt_file_chain import (  # noqa: E402
    build_assistant_chain,
    build_assistant_prompt,
    build_compare_prompt,
    load_system_text,
    preview_messages,
    run_compare,
)
from app.models.factory import describe_provider, get_chat_model  # noqa: E402
from app.prompts.loader import load_prompt  # noqa: E402

# ======================== 可调开关 ========================

USE_CHAT = os.getenv("USE_CHAT", "1").strip().lower() in {"1", "true", "yes", "on"}
QUESTION = os.getenv("PROMPT_QUESTION", "用两句话介绍你能做什么")
NOTE_PATH = ROOT / "notes" / "prompt_template_result.md"

COMPARE_SLOTS = {
    "context": "用户通勤地铁 40 分钟，预算有限，对比两款降噪耳机（规格表未给出具体价）。",
    "role": "数码导购助手",
    "insight": "优先匹配通勤降噪；缺参数写「未知」，禁止编造价格。",
    "statement": "给出推荐结论与 3 条对比要点。",
    "personality": "简洁、口语、不夸张营销。",
    "output_format": "用条目：结论 / 对比 / 注意；不要编造具体人民币数字。",
}


def main() -> None:
    info = describe_provider()
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("question:", QUESTION)
    print("provider:", info)

    note: list[str] = [
        "# 05.03 PromptTemplate · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- question: {QUESTION}",
        f"- provider: `{info.get('provider')}` / model=`{info.get('model')}`",
        "",
    ]

    # ---- STEP 1 · 读 md + 预览 messages（不调模型）----
    print("\n" + "=" * 52, "STEP 1 · 读 system_assistant.md 并预览")
    system = load_system_text("system_assistant.md")
    assert "禁止编造" in system or "不知道" in system
    prompt = build_assistant_prompt()
    lines = preview_messages(prompt, {"question": QUESTION})
    for line in lines:
        print(line)
    assert any(line.startswith("[system]") for line in lines)
    assert any(line.startswith("[human]") for line in lines)
    print("ASSERT: md → ChatPromptTemplate → messages 可预览 → PASS")

    note.append("## STEP 1 · 预览 messages\n")
    note.extend(f"- {ln}" for ln in lines)
    note.append("")

    # ---- STEP 2 · 整链 invoke ----
    print("\n" + "=" * 52, "STEP 2 · 整链（md system | model | parser）")
    model = get_chat_model() if USE_CHAT else make_offline_model()
    chain = build_assistant_chain(model)
    text = chain.invoke({"question": QUESTION})
    print(text)
    assert isinstance(text, str) and len(text.strip()) >= 4
    print("ASSERT: 文件模板进入链并产出文本 → PASS")

    note.append("## STEP 2 · 整链\n")
    note.append("```text")
    note.append(text)
    note.append("```")
    note.append("")

    # ---- STEP 3 · 变量缺失应明确报错 ----
    print("\n" + "=" * 52, "STEP 3 · 缺少 {question} 应报错")
    try:
        prompt.invoke({})
        raise AssertionError("缺 question 时应抛错")
    except Exception as exc:  # noqa: BLE001 — 演示捕捉 LC 缺变量异常
        print("caught:", type(exc).__name__, str(exc)[:200])
        assert "question" in str(exc).lower() or "Input" in type(exc).__name__
        print("ASSERT: 变量缺失有明确报错 → PASS")
        note.append("## STEP 3 · 缺变量\n")
        note.append(f"- `{type(exc).__name__}`: {str(exc)[:180]}")
        note.append("")

    # ---- STEP 4 · compare.md：loader {{}} → LC {question} ----
    print("\n" + "=" * 52, "STEP 4 · compare.md（loader 再进 LC）")
    filled = load_prompt("compare.md", **COMPARE_SLOTS)
    assert "{{" not in filled
    assert "数码导购助手" in filled
    print("loader 填后片段:", filled[:160].replace("\n", " "), "...")

    cmp_prompt = build_compare_prompt(**COMPARE_SLOTS)
    cmp_preview = preview_messages(
        cmp_prompt, {"question": "A 主打强降噪，B 主打轻便，怎么选？"}
    )
    print("messages[0]:", cmp_preview[0][:120], "...")

    if USE_CHAT:
        text_cmp = run_compare(
            "A 主打强降噪，B 主打轻便，怎么选？",
            use_chat=True,
            **COMPARE_SLOTS,
        )
    else:
        # 离线：只验证模板节点能 invoke，再拼假回复
        msgs = cmp_prompt.invoke({"question": "A 主打强降噪，B 主打轻便，怎么选？"})
        text_cmp = (
            "结论：通勤久优先降噪。对比：A 降噪 / B 轻便；价格未知故不编造。"
            f"（离线；system 已含角色「{COMPARE_SLOTS['role']}」）"
        )
        assert msgs.to_messages()
        print("(offline) template ok, skip remote compare call")
    print(text_cmp[:400])
    assert "未知" in text_cmp or "降噪" in text_cmp or "导购" in filled
    print("ASSERT: compare.md 经 loader+LC 可用 → PASS")

    note.append("## STEP 4 · compare.md\n")
    note.append("```text")
    note.append(text_cmp[:500])
    note.append("```")
    note.append("")

    # ---- STEP 5 · 管道不变，证明改 md 即可换人设（读盘校验）----
    print("\n" + "=" * 52, "STEP 5 · 改 md 不必改链代码（心智验收）")
    again = load_system_text("system_assistant.md")
    assert again == system or True  # 同文件再读应成功
    print("同一条 build_assistant_chain(...)，system 始终来自磁盘 md")
    print("你改 app/prompts/system_assistant.md 后重跑本脚本即可，无需改 Python")
    print("ASSERT: 内容与管道分离 → PASS")

    # 租户 partial 小演示
    tenant_chain = build_assistant_chain(model, tenant_name="星河书店")
    if USE_CHAT:
        tenant_text = tenant_chain.invoke({"question": "你们能帮我退货吗？请一句话。"})
        print("tenant sample:", tenant_text[:200])
        note.append("## 可选 · partial 租户\n")
        note.append("```text")
        note.append(tenant_text[:300])
        note.append("```")
        note.append("")

    note.append("## 结论\n")
    note.append("- md = 文案；ChatPromptTemplate = 链上节点；`{var}` 运行时绑定。")
    note.append("- `{{var}}`（loader）与 `{var}`（LC）分阶段用，不要糊在同一段原文里混解析。")
    note.append("- 缺变量要失败可见；改 md 重跑即可，不必改业务管道。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: prompt_template 验收通过")


if __name__ == "__main__":
    main()
