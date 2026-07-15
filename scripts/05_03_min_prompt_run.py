# scripts/05_03_min_prompt_run.py
"""05.03 最小可跑示例：读 system_assistant.md → 链 → 打印。

【怎么跑】必须在 ai-service 目录下（pwd 末尾是 ai-service）：

    cd /你的路径/AI从0到1/ai-service
    ls app/prompts/                          # 应能看到 system_assistant.md
    USE_CHAT=0 python scripts/05_03_min_prompt_run.py
    USE_CHAT=1 python scripts/05_03_min_prompt_run.py

完整验收（含缺变量、compare.md）见：scripts/05_03_prompt_template_demo.py
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

# 自检：模板文件必须存在（避免再踩「路径写重了」）
PROMPT_FILE = ROOT / "app" / "prompts" / "system_assistant.md"
if not PROMPT_FILE.is_file():
    raise SystemExit(
        f"找不到模板：{PROMPT_FILE}\n"
        "请先 cd 到 ai-service 再跑（不要 cd 到再上一层又写 ai-service/...）。\n"
        f"当前 ROOT={ROOT}"
    )

from app.chains.hello_chain import make_offline_model  # noqa: E402
from app.chains.prompt_file_chain import (  # noqa: E402
    build_assistant_chain,
    build_assistant_prompt,
    preview_messages,
    run_compare,
)
from app.models.factory import get_chat_model  # noqa: E402

USE_CHAT = os.getenv("USE_CHAT", "1").strip().lower() in {"1", "true", "yes", "on"}
QUESTION = os.getenv("PROMPT_QUESTION", "用两句话介绍你能做什么")


def main() -> None:
    print("cwd 提示: 应在 ai-service 下执行；模板路径 =", PROMPT_FILE)
    print("USE_CHAT:", USE_CHAT)

    # 1) 只看模板绑完后的 messages（不调模型）
    prompt = build_assistant_prompt()
    print("\n--- 预览 messages ---")
    for line in preview_messages(prompt, {"question": QUESTION}):
        print(line)

    # 2) 整链
    model = get_chat_model() if USE_CHAT else make_offline_model()
    text = build_assistant_chain(model).invoke({"question": QUESTION})
    print("\n--- 整链输出 ---")
    print(text)

    # 3) compare.md（可选；离线时仍演示 loader+模板）
    if USE_CHAT:
        cmp = run_compare(
            "A 主打强降噪，B 主打轻便，怎么选？",
            context="通勤地铁场景，价格未知",
            role="数码导购助手",
            insight="缺参数写未知，禁止编造价格",
            statement="给结论和三条对比",
            personality="口语、不施压",
            output_format="结论 / 对比 / 注意",
        )
        print("\n--- compare.md 输出 ---")
        print(cmp)
    else:
        print("\n--- compare.md ---")
        print("(USE_CHAT=0 跳过真实对比；完整步骤请跑 05_03_prompt_template_demo.py)")

    print("\nSUMMARY: 05.03 最小示例跑通")


if __name__ == "__main__":
    main()
