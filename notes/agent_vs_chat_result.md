# 06.01 Agent 是什么 · 实跑记录

- USE_CHAT: `False`
- question: 耳机 Pro 黑色 EARPHONE-PRO-BK 现在仓库里还有多少件？请给准确数字。
- ground_truth: `sku=EARPHONE-PRO-BK, stock=12`
- provider: `openai`

## 公式

`Agent ≈ Model + Tools + 控制策略（Loop）`


## STEP 1 · 三件套落点

- **Model**: get_chat_model() / bind_tools 后的大模型
- **Tools**: get_inventory / get_shipment（@tool）
- **控制策略(Loop)**: run_tool_agent 里 max_steps +「有 tool_calls 就执行再问、没有就停」

## STEP 2 · Chat only

- mode: `chat_only_offline`
- trace: `[]`
```text
（离线假 Chat）关于「耳机 Pro 黑色 EARPHONE-PRO-BK 现在仓库里还有多少件？请给准…」：黑色耳机热销款一般还有大概 3～5 件吧，建议尽快下单。【注意：此数字未查库存系统，仅演示幻觉风险】
```

## STEP 3 · Agent

- mode: `scripted`
- trace: `[{'tool': 'get_inventory', 'args': {'sku': 'EARPHONE-PRO-BK'}, 'observation': 'sku=EARPHONE-PRO-BK, stock=12'}]`
```text
查过了：sku=EARPHONE-PRO-BK, stock=12。以上数字来自库存工具，不是估算。
```

## STEP 4 · 对照

| | Chat | Agent |
|---|---|---|
| 工具轨迹 | 无 | 有 get_inventory |
| 与 mock 真值 | 易编造/漂移 | Observation=`sku=EARPHONE-PRO-BK, stock=12` |
| 形态 | 一次生成结束 | 思考→调工具→观察→再答 |


## 笔记三列（示例，请改成自己的）

### Chat 能做

- 解释「七天无理由」政策条文（资料已在 Prompt/RAG 里）
- 润色一段已有话术
- 把 JSON 字段翻译成人话（字段已给定）

### Agent 才需要

- 查实时库存/运单/号源（真相在业务 API）
- 先查订单再查物流再汇总（多步）
- 检索政策 + 再查系统状态组合回答

### 不该让 Agent 全自动做

- 不可逆转账/退款（需 HITL）
- 直接改库、强制发货
- 医疗诊断结论、法律责任承诺

## 结论

- Agent 不是「更强的模型」，是 Model + Tools + 控制策略。
- 05.07 调一次 Tool 是最小形态；本模块会把 Loop 跑稳。
- 不可逆操作默认不要全自动。
