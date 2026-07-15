# 06.03 Loop Engineering · 实跑记录


## 循环骨架

```text
while not done and steps < max_steps:
    Thought → (可选) Action → Observation → 写回上下文
    或 Final Answer → done
```

- 默认 `max_steps=6`
- 默认重复检测阈值 `max_identical=2`

## STEP 1 · 幸福路径轨迹

```text
--- STEP 1 · act ---
Thought: 目标含库存查询，先确认 sku 再调用 get_inventory
Action:  get_inventory({'sku': 'EARPHONE-PRO-BK'})
Observe: sku=EARPHONE-PRO-BK, stock=12
--- STEP 2 · act ---
Thought: 库存已拿到；下一步查运单 SF123456，禁止编 ETA
Action:  get_shipment({'tracking_no': 'SF123456'})
Observe: tracking_no=SF123456, status=已发货，转运中心
--- STEP 3 · final ---
Thought: 两段 Observation 齐全，汇总回答，不编造物流时效
Event:   Final Answer（退出循环）
```

- stop_reason: `final`
- answer: 根据工具结果：库存侧 sku=EARPHONE-PRO-BK, stock=12；物流侧 tracking_no=SF123456, status=已发货，转运中心。以上均来自 Observation，不是模型估算。

## STEP 2 · 重复检测

```text
--- STEP 1 · act ---
Thought: （错误）看到 not_found 仍打算用同一坏参数再查一遍
Action:  get_inventory({'sku': 'NO-SUCH-SKU'})
Observe: not_found
--- STEP 2 · act ---
Thought: （错误）看到 not_found 仍打算用同一坏参数再查一遍
Action:  get_inventory({'sku': 'NO-SUCH-SKU'})
Observe: not_found
--- STEP 3 · duplicate_stop ---
Thought: （错误）看到 not_found 仍打算用同一坏参数再查一遍
Action:  get_inventory({'sku': 'NO-SUCH-SKU'})
Brake:   重复调用打断 · get_inventory(sku='NO-SUCH-SKU')
```

- stop_reason: `duplicate_stop`
- answer: 检测到重复无效调用（连续>2 次相同：get_inventory(sku='NO-SUCH-SKU')）。已打断循环。请核对参数或转人工，勿空转烧钱。

## STEP 3 · max_steps 兜底

```text
--- STEP 1 · act ---
Thought: （拖延）再查一次库存 sku=EARPHONE-PRO-BK，迟迟不给出 Final Answer
Action:  get_inventory({'sku': 'EARPHONE-PRO-BK'})
Observe: sku=EARPHONE-PRO-BK, stock=12
--- STEP 2 · act ---
Thought: （拖延）再查一次库存 sku=EARPHONE-PRO-WH，迟迟不给出 Final Answer
Action:  get_inventory({'sku': 'EARPHONE-PRO-WH'})
Observe: sku=EARPHONE-PRO-WH, stock=0
--- STEP 3 · act ---
Thought: （拖延）再查一次库存 sku=CABLE-USB-C，迟迟不给出 Final Answer
Action:  get_inventory({'sku': 'CABLE-USB-C'})
Observe: sku=CABLE-USB-C, stock=56
```

- stop_reason: `max_steps`
- answer:

步数已用尽（max_steps=3）。我查到的信息如下：
- get_inventory({'sku': 'EARPHONE-PRO-BK'}) → sku=EARPHONE-PRO-BK, stock=12
- get_inventory({'sku': 'EARPHONE-PRO-WH'}) → sku=EARPHONE-PRO-WH, stock=0
- get_inventory({'sku': 'CABLE-USB-C'}) → sku=CABLE-USB-C, stock=56
如需继续请缩小问题或转人工。

## STEP 4 · 旋钮检查清单

| 旋钮 | 作用 | 本课落点 |
|------|------|----------|
| max_steps | 防止无限循环 / 账单爆炸 | 6 |
| 重复调用检测 | 相同 Tool+参数连打 → 打断 | max_identical=2 |
| 观察原样回灌 | not_found / error 字符串进轨迹 | 见 STEP 1–2 observation 字段 |
| 最终兜底 | 步数用尽 → 事实清单 + 转人工 | 见 STEP 3 answer |
| 轨迹一等公民 | 每步 Thought/Action/Observation 可回放 | notes 里已落盘 |

## 结论

- Loop Engineering = 可约束 + 可观测 + 可停止，不是「再调大一点 max_steps」。
- 内循环 = 一次任务内的 Think/Act/Observe；外会话 = 多轮记忆（别混）。
- 分支多、要 HITL/持久化时再上 LangGraph（M07）；Loop 仍是图里的心脏。
