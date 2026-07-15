# 05.07 Tool 与 ReAct 初体验 · 实跑记录

- USE_CHAT: `False`
- question: 耳机 Pro 黑色（EARPHONE-PRO-BK）还有货吗？还有多少件？
- provider: `openai`

## STEP 1 · schema

- name: `get_inventory`
- description: 查询商品 SKU 的库存数量（只读）。

    何时用：用户问「还有货吗 / 库存多少 / 黑色还有没有」且能对应到 sku。
    何时不用：闲聊、问政策条款（应走文档检索）、改库存/下单（本课无写权限）。

    参数:
        sku: 商品编码，例如 EARPHONE-PRO-BK

    返回:
        成功: 「sku=..., stock=N」；未知 sku: 「not_found」
- args: `{'sku': {'title': 'Sku', 'type': 'string'}}`

## STEP 2 · 直接调用

- BK: `sku=EARPHONE-PRO-BK, stock=12`
- WH: `sku=EARPHONE-PRO-WH, stock=0`
- missing: `not_found`

## STEP 3 · Agent

- mode: `scripted`
- trace: `[{'tool': 'get_inventory', 'args': {'sku': 'EARPHONE-PRO-BK'}, 'observation': 'sku=EARPHONE-PRO-BK, stock=12'}]`
```text
查过了：sku=EARPHONE-PRO-BK, stock=12。以上数字来自库存工具，不是估算。
```

## STEP 4 · runner

- trace: `[{'tool': 'get_inventory', 'args': {'sku': 'CABLE-USB-C'}, 'observation': 'sku=CABLE-USB-C, stock=56'}]`
```text
查过了：sku=CABLE-USB-C, stock=56。以上数字来自库存工具，不是估算。
```

## 结论

- Tool = 说明书 + 函数；描述写清何时用/不用。
- ReAct 初体验：Thought → Action(Tool) → Observation → Final Answer。
- 完整 Loop 工程（步数、超时、HITL）放 M06。
