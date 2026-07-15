# 07.02 StateGraph 基础 · 实跑记录


## 生命周期

```text
定义 State → StateGraph → add_node → add_edge → compile → invoke
```

## STEP 1 · Hello

- input: `{'text': 'hello graph'}`
- output: `{'text': 'HELLO GRAPH'}`
- lesson: 节点返回 {text: 大写}，合并进 State（默认覆盖同名字段）

## STEP 2 · 合并要点

- 节点返回 dict = 本轮要对 State 做的补丁（partial update）
- 默认同名字段：后到的值覆盖先到的值
- 列表要追加：用 Annotated[list, operator.add] 或 add_messages
- 不要 return 整个旧 State 再改一处——难读且易误伤未改字段

## STEP 3 · reducer 追加

- `{'title': '退货咨询', 'notes': ['intake: 已登记用户诉求', 'check: 材料待人工核验']}`

## STEP 4 · 覆盖反例

- `{'title': '退货咨询', 'notes': ['check: 只有我']}`
- lesson: intake 的笔记消失了 → 缺 reducer 时后写覆盖

## STEP 5 · State 字段

- HelloState: `['text']`
- NotesState: `['title', 'notes']`

## 结论

- State + compile 后的图 = 最小可运行单元。
- 列表字段必须声明合并规则，否则后写覆盖。
- 下一课：扩成检索 → 分析 → 生成三节点流水线。
