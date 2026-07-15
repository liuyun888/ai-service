# app/models/factory.py
"""课次 05.02 · 多模型 Chat 工厂：按配置创建统一 ChatModel。

直觉（0 基础版）：
- 业务代码只认「会聊的插座」→ model.invoke(messages)
- 具体插哪家插头由本文件根据 DEFAULT_LLM（或入参 provider）决定
- 换模型 = 拧环境变量旋钮，调用方代码不用改

【与本专栏旧 .env 的兼容】
M01～M04 / 05.01 的聊天一律走：
  OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL
（讯飞 Coding Plan 等 OpenAI 兼容网关）。
因此：
- provider=`openai`（或别名 xfyun）→ 只读上面三连
- DEFAULT_LLM=glm 但还没配可用的智谱 Key 时 → 自动回退到 OPENAI_*，
  避免「旋钮写了 glm、水却一直在讯飞桶里」却突然报错

其它厂商需要各自 Key；缺 Key 且没有 OPENAI_* 可回退时，报错写清缺什么。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

# 无论从哪启动，都先加载 ai-service/.env（常见坑：Key 配了但读不到）
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

# 工厂认识的 provider 名（小写）。openai = 原 .env 的 OPENAI_* 兼容网关
KNOWN_PROVIDERS = ("glm", "deepseek", "claude", "openai")


def _env(name: str) -> str:
    """读环境变量并去掉首尾空白。"""
    return os.getenv(name, "").strip()


def _require(name: str) -> str:
    """读取必填环境变量；空则抛清晰错误，方便对照 .env.example。"""
    value = _env(name)
    if not value:
        raise RuntimeError(
            f"缺少环境变量 {name}：请对照 .env.example 填写后重试"
        )
    return value


def _is_placeholder_key(value: str) -> bool:
    """占位符 / 明显未填写的 Key，不当作「已配置」。"""
    if not value:
        return True
    upper = value.upper()
    return (
        upper.startswith("YOUR_")
        or upper in {"YOUR_API_KEY", "YOUR_ZHIPU_API_KEY", "CHANGE_ME"}
        or "占位" in value
    )


def _has_openai_compat() -> bool:
    """旧专栏链路是否可直接用：OPENAI_API_KEY + OPENAI_BASE_URL 都有。"""
    return bool(_env("OPENAI_API_KEY") and _env("OPENAI_BASE_URL"))


def _has_zhipu() -> bool:
    """是否真的配了智谱（非占位）。与讯飞 Key 雷同时不算智谱已接通。"""
    key = _env("ZHIPUAI_API_KEY")
    if _is_placeholder_key(key):
        return False
    # 常见误配：把讯飞 Key 复制进 ZHIPUAI_API_KEY，实际仍应走 OPENAI_*
    openai_key = _env("OPENAI_API_KEY")
    if openai_key and key == openai_key and _has_openai_compat():
        return False
    return True


def _chat_openai(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    temperature: float,
) -> BaseChatModel:
    """用 OpenAI 兼容协议创建 Chat 模型（多数国产网关都长这样）。"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )


def _make_openai_compat(*, temperature: float) -> BaseChatModel:
    """原 .env 三连：OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL。

    这是本专栏从 M01 起一直在用的聊天入口（讯飞等兼容网关）。
    """
    return _chat_openai(
        api_key=_require("OPENAI_API_KEY"),
        base_url=_require("OPENAI_BASE_URL"),
        model=_env("OPENAI_MODEL") or "sensen-code-latest",
        temperature=temperature,
    )


def _make_glm(*, temperature: float) -> BaseChatModel:
    """智谱 GLM：需要可用的 ZHIPUAI_API_KEY。

    若未接通智谱、但已有 OPENAI_* → 回退兼容网关（见 get_chat_model）。
    """
    return _chat_openai(
        api_key=_require("ZHIPUAI_API_KEY"),
        base_url=_env("ZHIPUAI_BASE_URL")
        or "https://open.bigmodel.cn/api/paas/v4",
        model=_env("GLM_MODEL") or "glm-4-flash",
        temperature=temperature,
    )


def _make_deepseek(*, temperature: float) -> BaseChatModel:
    """DeepSeek：OpenAI 兼容地址 + DEEPSEEK_API_KEY。"""
    return _chat_openai(
        api_key=_require("DEEPSEEK_API_KEY"),
        base_url=_env("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
        model=_env("DEEPSEEK_MODEL") or "deepseek-chat",
        temperature=temperature,
    )


def _make_claude(*, temperature: float) -> BaseChatModel:
    """Claude：优先 OpenAI 兼容网关；否则尝试官方 Anthropic SDK。"""
    claude_key = _env("CLAUDE_API_KEY")
    claude_base = _env("CLAUDE_BASE_URL")
    if claude_key and claude_base:
        return _chat_openai(
            api_key=claude_key,
            base_url=claude_base,
            model=_env("CLAUDE_MODEL") or "claude-3-5-sonnet-latest",
            temperature=temperature,
        )

    anthropic_key = _env("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise RuntimeError(
                "检测到 ANTHROPIC_API_KEY，但未安装 langchain-anthropic。"
                "请执行: pip install 'langchain-anthropic>=0.3,<1.0'；"
                "或改用 CLAUDE_BASE_URL + CLAUDE_API_KEY（OpenAI 兼容网关）"
            ) from exc
        return ChatAnthropic(
            model=_env("CLAUDE_MODEL") or "claude-3-5-sonnet-latest",
            api_key=anthropic_key,
            temperature=temperature,
        )

    raise RuntimeError(
        "Claude 未配置：请设 CLAUDE_BASE_URL + CLAUDE_API_KEY，"
        "或安装 langchain-anthropic 并设 ANTHROPIC_API_KEY"
    )


def resolve_provider(provider: str | None = None) -> str:
    """解析最终要走的 provider 名（可能因兼容而从 glm 落到 openai）。

    规则：
    1. 入参 / DEFAULT_LLM 指定 openai（或 xfyun）→ openai
    2. 指定 glm 但智谱未真正接通、且有 OPENAI_* → 回退 openai
    3. 其它名字原样返回（缺 Key 时由对应 _make_* 报错）
    """
    raw = (provider or _env("DEFAULT_LLM") or "openai").strip().lower()
    if raw in {"openai", "openai_compat", "xfyun"}:
        return "openai"
    if raw == "glm" and not _has_zhipu() and _has_openai_compat():
        # 兼容：DEFAULT_LLM 仍写 glm，但真实聊天一直在 OPENAI_*
        return "openai"
    return raw


def get_chat_model(
    provider: str | None = None,
    *,
    temperature: float = 0.2,
) -> BaseChatModel:
    """按 provider 创建 Chat 模型（统一返回 BaseChatModel）。

    参数：
        provider: glm / deepseek / claude / openai；None 则读 DEFAULT_LLM
        temperature: 随机度；演示建议 0.2

    返回：
        可放入 LCEL 的 Chat 模型（支持 invoke / 管道 |）

    异常：
        ValueError: 未知 provider
        RuntimeError: Key / 依赖缺失（信息里写清缺什么）
    """
    requested = (provider or _env("DEFAULT_LLM") or "openai").strip().lower()
    name = resolve_provider(provider)

    if name == "openai":
        if requested == "glm" and not _has_zhipu():
            # 不静默得太狠：调用方可从 describe_provider 看到 fallback
            pass
        return _make_openai_compat(temperature=temperature)
    if name == "glm":
        return _make_glm(temperature=temperature)
    if name == "deepseek":
        return _make_deepseek(temperature=temperature)
    if name == "claude":
        return _make_claude(temperature=temperature)

    raise ValueError(
        f"unknown provider: {requested!r}；可选: {', '.join(KNOWN_PROVIDERS)}"
    )


def describe_provider(provider: str | None = None) -> dict[str, str]:
    """调试用：当前解析到谁、用哪套环境变量、模型名（不打印完整 Key）。"""
    requested = (provider or _env("DEFAULT_LLM") or "openai").strip().lower()
    name = resolve_provider(provider)
    fallback = "1" if (
        requested == "glm" and name == "openai" and _has_openai_compat()
    ) else "0"

    if name == "openai":
        model = _env("OPENAI_MODEL") or "sensen-code-latest"
        cred = "OPENAI_BASE_URL+OPENAI_API_KEY+OPENAI_MODEL"
    elif name == "glm":
        model = _env("GLM_MODEL") or "glm-4-flash"
        cred = "ZHIPUAI_API_KEY(+ZHIPUAI_BASE_URL/GLM_MODEL)"
    elif name == "deepseek":
        model = _env("DEEPSEEK_MODEL") or "deepseek-chat"
        cred = "DEEPSEEK_API_KEY(+DEEPSEEK_BASE_URL/DEEPSEEK_MODEL)"
    elif name == "claude":
        model = _env("CLAUDE_MODEL") or "claude-3-5-sonnet-latest"
        cred = "CLAUDE_* 或 ANTHROPIC_API_KEY"
    else:
        model = "?"
        cred = "?"

    return {
        "requested": requested or name,
        "provider": name,
        "model": model,
        "credentials": cred,
        "fallback_to_openai": fallback,
        "openai_base_url": _env("OPENAI_BASE_URL") if name == "openai" else "",
    }
