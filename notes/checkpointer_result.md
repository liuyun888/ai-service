# 07.05 Checkpointer · 实跑记录


## 公式

`config = {"configurable": {"thread_id": "..."}}`

续跑优先：`app.invoke({}, config)`，勿再传会覆盖的初始字段。


## STEP 1

- checkpointer 类型: `InMemorySaver`（文档仍称 MemorySaver）

## STEP 2 · 同线程

- first: `{'count': 1, 'log': ['count=1']}`
- second: `{'count': 2, 'log': ['count=1', 'count=2']}`

## STEP 3 · get_state

- values: `{'count': 2, 'log': ['count=1', 'count=2']}`
- next: `()`

## STEP 4 · 隔离

- A: `{'count': 2, 'log': ['count=1', 'count=2']}`
- B: `{'count': 1, 'log': ['count=1']}`
- 猜不到/鉴权住 thread_id，才能防跨租户续跑

## STEP 5 · 覆盖陷阱

- wrong: `{'count': 1, 'log': ['count=1', 'count=2', 'count=1']}`
- right: `{'count': 2, 'log': ['count=1', 'count=2', 'count=1', 'count=2']}`
- 勿用初始值覆盖 checkpoint

## STEP 6 · 生产清单

- MemorySaver 仅开发：进程内、重启丢、多副本不共享
- 生产换 Postgres/Redis 等官方或社区 Checkpointer
- thread_id 不可预测，并在 BFF 校验租户归属
- 敏感字段进 State 前脱敏或外置
- 聊天记忆 ≠ Checkpoint：后者存整图位置，丢了可能无法续跑

## 结论

- Checkpoint 存整图 State+位置；聊天记忆只存话。
- 下一课：在 checkpoint 上 interrupt / 人工确认后再 resume。
