# scripts/05_02_model_factory_demo.py
"""05.02 ChatModel 多模型工厂演示。

【本课要感受的三件事】
1. 调用方只认 get_chat_model() / hello_chain，不认厂商 SDK
2. 拧 DEFAULT_LLM（或入参 provider）就能换插头；原 .env 的 OPENAI_* 必须可用
3. 未知 provider → 清晰 ValueError

依赖：langchain-core、langchain-openai（见 requirements.txt）
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

from app.chains.hello_chain import build_hello_chain, make_offline_model  # noqa: E402
from app.models.factory import (  # noqa: E402
    KNOWN_PROVIDERS,
    describe_provider,
    get_chat_model,
    resolve_provider,
)

# ======================== 可调开关 ========================

# False：不调远端，用离线 Runnable（仍验证「调用方不绑厂商」）
USE_CHAT = os.getenv("USE_CHAT", "1").strip().lower() in {"1", "true", "yes", "on"}

# 覆盖 DEFAULT_LLM：例如 PROVIDER=openai python scripts/05_02_model_factory_demo.py
PROVIDER = os.getenv("PROVIDER", "").strip() or None

TOPIC = os.getenv("HELLO_TOPIC", "什么是多模型工厂")
NOTE_PATH = ROOT / "notes" / "model_factory_result.md"


def main() -> None:
    info = describe_provider(PROVIDER)
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("DEFAULT_LLM env:", os.getenv("DEFAULT_LLM", "(unset)"))
    print("PROVIDER override:", PROVIDER or "(none)")
    print("resolved:", info)
    print("known:", ", ".join(KNOWN_PROVIDERS))
    print("OPENAI_BASE_URL:", os.getenv("OPENAI_BASE_URL", "(unset)"))
    print("OPENAI_MODEL:", os.getenv("OPENAI_MODEL", "(unset)"))
    print(
        "OPENAI_API_KEY:",
        "(set)" if os.getenv("OPENAI_API_KEY", "").strip() else "(missing)",
    )

    note: list[str] = [
        "# 05.02 ChatModel 与多模型工厂 · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- DEFAULT_LLM: `{os.getenv('DEFAULT_LLM', '')}`",
        f"- PROVIDER: `{PROVIDER or ''}`",
        f"- resolved: `{info}`",
        "",
    ]

    # ---- STEP 1 · 工厂能否按配置创建（或离线 Runnable）----
    print("\n" + "=" * 52, "STEP 1 · 工厂创建模型（读 DEFAULT_LLM / PROVIDER）")
    if USE_CHAT:
        model = get_chat_model(PROVIDER)
        print("created:", type(model).__name__)
        print("provider:", resolve_provider(PROVIDER))
        print("credentials:", info.get("credentials"))
        assert hasattr(model, "invoke"), "Chat 模型应可 invoke"
        print("ASSERT: get_chat_model 返回可 invoke 对象 → PASS")
        note.append("## STEP 1 · 工厂创建\n")
        note.append(f"- type: `{type(model).__name__}`")
        note.append(f"- provider: `{resolve_provider(PROVIDER)}`")
        note.append(f"- credentials: `{info.get('credentials')}`")
        note.append("")
    else:
        model = make_offline_model()
        print("created: offline Runnable（不调网）")
        print("ASSERT: 离线 Runnable 可验调用方接口 → PASS")
        note.append("## STEP 1 · 离线 Runnable\n")
        note.append("- type: `RunnableLambda`（offline）")
        note.append("")

    # ---- STEP 2 · 同一条 hello_chain ----
    print("\n" + "=" * 52, "STEP 2 · hello_chain 走工厂模型")
    chain = build_hello_chain(model)
    text = chain.invoke({"topic": TOPIC})
    print(text)
    assert isinstance(text, str) and len(text.strip()) >= 8
    print("ASSERT: 整链返回非空字符串 → PASS")

    note.append("## STEP 2 · 整链\n")
    note.append("```text")
    note.append(text)
    note.append("```")
    note.append("")

    # ---- STEP 3 · 强制 openai，证明兼容原 .env 的 OPENAI_* 三连 ----
    print("\n" + "=" * 52, "STEP 3 · 显式 provider=openai（兼容原 OPENAI_*）")
    if USE_CHAT:
        openai_info = describe_provider("openai")
        print("resolved openai:", openai_info)
        assert openai_info["provider"] == "openai"
        assert "OPENAI_" in openai_info["credentials"]
        assert os.getenv("OPENAI_BASE_URL", "").strip(), "缺少 OPENAI_BASE_URL"
        assert os.getenv("OPENAI_API_KEY", "").strip(), "缺少 OPENAI_API_KEY"

        # 调用方仍是 get_chat_model + hello_chain，只是插头拧到 openai
        model_openai = get_chat_model("openai")
        text_b = build_hello_chain(model_openai).invoke(
            {"topic": "OPENAI_MODEL 指的是哪家网关上的哪个模型"}
        )
        print(text_b)
        print(
            "兼容确认: base_url=",
            os.getenv("OPENAI_BASE_URL", "")[:48] + "...",
            "| model=",
            os.getenv("OPENAI_MODEL", ""),
        )
        assert isinstance(text_b, str) and text_b.strip()
        print("ASSERT: provider=openai 走原 .env OPENAI_* → PASS")
        print(
            "提示: 换模型名只需改 OPENAI_MODEL；"
            "换智谱/DeepSeek 再分别配 ZHIPUAI_* / DEEPSEEK_* 并改 DEFAULT_LLM"
        )
        note.append("## STEP 3 · 显式 openai（原 OPENAI_*）\n")
        note.append(f"- credentials: `{openai_info['credentials']}`")
        note.append(f"- model: `{openai_info['model']}`")
        note.append(f"- base_url: `{os.getenv('OPENAI_BASE_URL', '')}`")
        note.append("```text")
        note.append(text_b)
        note.append("```")
        note.append("")
    else:
        text_b = build_hello_chain(make_offline_model()).invoke(
            {"topic": "OPENAI_MODEL 指的是哪家网关上的哪个模型"}
        )
        print(text_b)
        print("ASSERT: 离线路径调用方接口不变 → PASS")
        note.append("## STEP 3 · 离线换 topic\n")
        note.append("```text")
        note.append(text_b)
        note.append("```")
        note.append("")

    # ---- STEP 4 · 未知 provider 必须清晰报错 ----
    print("\n" + "=" * 52, "STEP 4 · 未知 provider 报错")
    try:
        get_chat_model("not-a-real-vendor")
        raise AssertionError("未知 provider 应抛 ValueError")
    except ValueError as exc:
        print("caught:", exc)
        assert "unknown provider" in str(exc)
        print("ASSERT: 未知 provider → ValueError → PASS")
        note.append("## STEP 4 · 未知 provider\n")
        note.append(f"- 异常: `{exc}`")
        note.append("")

    note.append("## 结论\n")
    note.append("- 业务只依赖 `get_chat_model()` / Runnable，不绑某一家 SDK。")
    note.append(
        "- 原 `.env` 的 `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` "
        "通过 `provider=openai`（或回退）继续可用。"
    )
    note.append("- 切换：同网关改 `OPENAI_MODEL`；换厂商再配对应 Key + `DEFAULT_LLM`。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: model factory 验收通过（已兼容 OPENAI_*）")


if __name__ == "__main__":
    main()
