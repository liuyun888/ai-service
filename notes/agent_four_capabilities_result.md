# 06.02 Agent 四能力 · 实跑记录


## 公式复习

`Agent ≈ Model + Tools + 控制策略`；四能力用来检查「装得全不全」。


## STEP 1 · 对照表

| 能力 | 我的场景表现 | 当前实现 | 缺口 |
|------|--------------|----------|------|
| 规划 | 用户问库存时先选 get_inventory，再组织话术 | 隐式：模型+ReAct 自选下一步（无显式 todo） | 复杂多目标时易漏步；未强制「先确认 sku 再查」 |
| 工具 | 能拿到真实 mock 库存数字 | get_inventory / get_shipment（@tool） | 尚无 get_order；政策类应接检索 Tool |
| 记忆 | 单轮 messages 里能看见上一轮 Tool 结果 | 进程内 messages 列表（会话级） | 跨请求未落 Redis/摘要；用户偏好未结构化 |
| 反思 | 看到 not_found 时，理想应换策略而不是盲重试 | 主要靠模型读 Observation（代码层未强制） | 缺代码闸门：同一坏 sku 仍可能被连调多次 |

## STEP 2 · 反思对照

- 缺反思: `对 NO-SUCH-SKU 连续调用 5 次，观察值不变仍死磕`
- 有反思: `SKU「NO-SUCH-SKU」查无（not_found）。请核对编码后重试，我不会再对同一坏参数连打接口。`

## STEP 3 · 记忆

- 无记忆: 无法查询：未提供 sku（模拟失忆客服）
- 有记忆: 根据你刚才提供的 EARPHONE-PRO-BK：sku=EARPHONE-PRO-BK, stock=12

## STEP 4 · 规划

- 1) 确认商品 sku → get_inventory
- 2) 确认运单号 → get_shipment
- 3) 汇总两段 Observation，禁止编造
- 汇总: 规划执行完毕：库存侧 sku=EARPHONE-PRO-BK, stock=12；物流侧 tracking_no=SF123456, status=已发货，转运中心。两步按顺序完成，没有跳过查库直接瞎报数。

## STEP 5 · 故障归类

- `反思` ← 模型越查 not_found 越调同一 sku
- `记忆` ← 客服每轮都重新要订单号
- `工具` ← 只会聊天说「大概有货」从不调工具
- `规划` ← 该先查单再查物流，结果直接编物流

## 结论

- 四能力是设计检查清单：缺哪项，故障长哪样。
- 反思要用 Observation 驱动分支，不是写鸡汤。
- 简单任务可裁剪；复杂办结再加规划/记忆/图与 Harness。
