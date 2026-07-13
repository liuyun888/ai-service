# Chat 模型 vs Embedding 模型（本仓库实况）

> 对应代码：`app/llm/client.py`（Chat）与 `app/lessons/m02_03_embeddings.py`（Embedding）  
> 对应专栏：`02-04 Embedding vs Chat 模型`

## 一句话

**Chat 负责「说」；Embedding（控制台常叫「向量模型」）负责「量远近」。**  
SDK 都可能叫 `OpenAI`、接口都「兼容」，但开的是不同门——不能拿 `client.py` 里的对话模型直接当向量模型用。

## 2026 年：市面上有没有专门的 Embedding？

**有。** 只是中文控制台经常不写英文 “Embedding”，而写 **「向量模型」**。

| 你看到的页面 | 容易误判 | 实际情况 |
|--------------|----------|----------|
| 企业专区 GLM 包量卡 | 「全是对话模型」 | 营销套餐，主推 Chat/多模态，不列向量 |
| GLM-5.2 等文本模型文档 | 「只有文本模型」 | 左侧分类另有 **向量模型** |
| 智谱向量模型 | — | 仍有 **Embedding-3 / Embedding-2**，API：`/paas/v4/embeddings` |
| 开源 / 本课 local | — | 如 `BAAI/bge-small-zh-v1.5`，同样是专用向量模型 |

文档入口示例：[模型概览 · 向量模型](https://docs.bigmodel.cn/cn/guide/start/model-overview)、[Embedding-3](https://docs.bigmodel.cn/cn/guide/models/embedding/embedding-3)。

## 本仓库当前配置

| 用途 | 入口 | 环境变量 / 默认 |
|------|------|-----------------|
| 对话生成 | `app/llm/client.py` → `call_chat` | `OPENAI_BASE_URL`（如讯飞 Coding Plan `maas-coding-api.../v2`）+ `OPENAI_MODEL`（如 `astron-code-latest`） |
| 文本向量化 | `app/lessons/m02_03_embeddings.py` → `embed_texts` | `EMBEDDING_PROVIDER=local` + `EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`（或云端 `openai` + Embedding 专用地址） |

实测：用 Chat 同一套 `OPENAI_BASE_URL` + Key 去调 `embeddings.create`，网关常返回 **404 / 不可用**——说明该 Coding 网关开了对话，未必开了向量化。

## 区别对照

| | Chat（`client.py`） | Embedding（`m02_03_embeddings.py`） |
|--|---------------------|------------------------------|
| 出口 | 文本 / token 序列 | 固定维度浮点向量（如 512 / 1024） |
| 典型 API | `chat.completions.create` | `embeddings.create` |
| 擅长 | 问答、写作、总结、工具调用对话 | 语义相似、检索、聚类、入库 |
| 计费 | 常按输入 + 输出 token | 常按输入文本向量化 |
| 本仓库怎么用 | Prompt / 客服回复 / 结构化生成 | RAG 检索前的向量、相似度比较 |
| 能否互相替代 | **不能**拿来做稳定检索 | **不能**直接当用户可见回复 |

## 正确组合（RAG）

```text
文档 --Embedding--> 向量库
问题 --Embedding--> 查询向量 --> 检索片段
片段 + 问题 --Chat--> 最终回答
```

## 典型错误

1. 用 Chat 扫全库「哪段相关」→ 贵、慢、不可复现  
2. 用 Embedding 向量当客服回复发给用户 → 用户看不懂  
3. 索引与查询各用不同 Embedding 型号 → 分数失真  
4. 以为「一个 Key / 一个 client 万能」→ Chat 网关 ≠ Embedding 服务

## 团队约定（建议）

```text
检索 / 相似度 → Embedding（app/lessons/m02_03_embeddings.py）
对话 / 推理 / JSON 生成 → Chat（client.py）
禁止：用 Chat 扫描全库当搜索引擎
禁止：用伪随机 / 哈希假向量冒充 Embedding
```

## 怎么选（本课落地）

- 要对话 → `from app.llm.client import call_chat`
- 要向量 → `from app.lessons.m02_03_embeddings import embed_texts`  
  - 无云端 Embedding 权限：保持 `EMBEDDING_PROVIDER=local`  
  - 有智谱等 Embedding Key：改 `openai`，并配置 `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` / `EMBEDDING_MODEL`
