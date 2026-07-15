# 05.02 ChatModel 与多模型工厂 · 实跑记录

- USE_CHAT: `True`
- DEFAULT_LLM: `openai`
- PROVIDER: ``
- resolved: `{'requested': 'openai', 'provider': 'openai', 'model': 'astron-code-latest', 'credentials': 'OPENAI_BASE_URL+OPENAI_API_KEY+OPENAI_MODEL', 'fallback_to_openai': '0', 'openai_base_url': 'https://maas-coding-api.cn-huabei-1.xf-yun.com/v2'}`

## STEP 1 · 工厂创建

- type: `ChatOpenAI`
- provider: `openai`
- credentials: `OPENAI_BASE_URL+OPENAI_API_KEY+OPENAI_MODEL`

## STEP 2 · 整链

```text
多模型工厂就是一个集中管理和调度多个AI大模型的平台，就像个“模型大超市”。它能根据你不同的任务需求，自动挑选最合适的模型来干活，帮你省去一个个切换的麻烦。简单说，它让你不用死磕一个模型，而是让各个模型打配合、发挥各自优势。
```

## STEP 3 · 显式 openai（原 OPENAI_*）

- credentials: `OPENAI_BASE_URL+OPENAI_API_KEY+OPENAI_MODEL`
- model: `astron-code-latest`
- base_url: `https://maas-coding-api.cn-huabei-1.xf-yun.com/v2`
```text
“OPENAI_MODEL”通常指的是 OpenAI 官方 API 网关（即 api.openai.com）上部署的各类大语言模型，比如 GPT-4o 或 GPT-3.5-turbo。在实际开发中，它往往是你代码或配置文件里的一个环境变量名，用来指定你要调用该网关上的具体哪个模型。所以它本身不是某个特定模型的专有名称，而是代表你需要填入的、跑在 OpenAI 官方网关上的目标模型标识。
```

## STEP 4 · 未知 provider

- 异常: `unknown provider: 'not-a-real-vendor'；可选: glm, deepseek, claude, openai`

## 结论

- 业务只依赖 `get_chat_model()` / Runnable，不绑某一家 SDK。
- 原 `.env` 的 `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` 通过 `provider=openai`（或回退）继续可用。
- 切换：同网关改 `OPENAI_MODEL`；换厂商再配对应 Key + `DEFAULT_LLM`。
