# 06.05 Tool 设计原则 · 实跑记录


## 评审清单

- `name_verb`: 名字是动词短语且唯一（get_x / search_y）
- `params_few`: 参数少而必要，类型明确（不要一坨 free JSON）
- `desc_when`: 描述写清何时用 / 何时不用
- `return_samples`: 有成功/失败样例返回格式
- `error_string`: 失败返回可读字符串，不抛栈打崩进程
- `readonly_split`: 只读与有副作用写入分开（或声明禁止写）
- `no_nested_llm`: Tool 内不再调大模型（保持确定性 I/O）
- `no_secret_param`: 不让模型传密钥；凭证由服务端注入

## STEP 1 · Schema 摘要

### manage

```
处理商品相关。
```

### get_course

```
查询一门课的课表信息（只读）。

    何时用：用户给出课程编号（如 CS101）问「什么时候上 / 在哪个教室」。
    何时不用：选课下单、改课、冲突计算（应另做 write/conflict Tool）；闲聊。

    参数:
        course_id: 课程编码，大写字母+数字，例如 CS101

    返回:
        成功: 「course_id=..., schedule=...」
        失败: 「error=not_found; hint=…」或「error=empty; hint=…」（字符串，不抛异常）
```

## STEP 2 · 打分

| Tool | 得分 | 备注 |
|------|------|------|
| manage | 3/8 | 名字不像单一动词短语，或过于含糊（manage/do_everything）; 描述缺少「何时用 / 何时不用」; 描述未说明成功/失败返回格式 |
| do_everything | 3/8 | 名字不像单一动词短语，或过于含糊（manage/do_everything）; 描述缺少「何时用 / 何时不用」; 描述未说明成功/失败返回格式 |
| get_inventory | 8/8 | — |
| get_shipment | 8/8 | — |
| search_knowledge | 8/8 | — |
| get_course | 8/8 | — |

## STEP 3 · 错误回灌

- 坏 manage: `{'ok': False, 'observation': None, 'raised': 'RuntimeError: 仓库超时 stacktrace=...'}`
- 好 get_course: `error=not_found; hint=核对课程编号大小写与数字，当前目录含 CS101/CS201/MATH100`

## STEP 4 · 粒度

- 目标: 查 EARPHONE-PRO-BK 库存，并查 CS101 什么时候上课
- 细粒度: `[{'ok': True, 'observation': 'sku=EARPHONE-PRO-BK, stock=12', 'raised': None}, {'ok': True, 'observation': 'course_id=CS101, schedule=周一 09:00-11:00 / 教室 A101 / 容量 40', 'raised': None}]`
- 教训: 组合由 Loop 做；不要把工作流藏进 do_everything

## STEP 5 · 副作用

- `{'ok': True, 'observation': 'refunded=true; money=-1', 'raised': None}`
- 有副作用 → 默认禁止或 HITL（06.06），勿与只读查询混在同一超级 Tool

## STEP 6 · 改好记录

- 新增好 Tool: `app/tools/course_schedule.py` → `get_course`
- 库存错误串对照 before=`not_found` / after=`error=not_found; hint=检查 sku 是否含颜色后缀如 -BK/-WH；你传入的是 'EARPHONE'，目录示例 EARPHONE-PRO-BK`
- 成功样例: `course_id=CS101, schedule=周一 09:00-11:00 / 教室 A101 / 容量 40`
- 说明: 生产 get_inventory 仍返回精确 not_found 以兼容前几课；新 Tool 请用 error=/hint= 格式

## 结论

- Tool 是 Agent 的手：描述清晰、一事一工具、失败可回灌。
- 超级 Tool 与硬抛异常是常见翻车源。
- 有副作用操作单独拆出并上 HITL（06.06）。
