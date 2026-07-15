# 05.03 PromptTemplate · 实跑记录

- USE_CHAT: `True`
- question: 用两句话介绍你能做什么
- provider: `openai` / model=`astron-code-latest`

## STEP 1 · 预览 messages

- [system] 你是简洁的在线助手。

规则：
1. 不知道就说不知道，禁止编造业务数据。
2. 默认简体中文，分点作答，单次不超过 8 条。
3. 涉及下单、支付、医疗诊断、法律结论时，提示用户走正式渠道。
- [human] 用两句话介绍你能做什么

## STEP 2 · 整链

```text
1. 我能以简体中文为您分点解答各类常识与信息问题。
2. 涉及下单、支付、医疗或法律等专业领域时，我会提示您走正式渠道。
```

## STEP 3 · 缺变量

- `KeyError`: "Input to ChatPromptTemplate is missing variables {'question'}.  Expected: ['question'] Received: []\nNote: if you intended {question} to be part of the string and not a variable, 

## STEP 4 · compare.md

```text
结论：选A。通勤地铁40分钟环境噪音大，强降噪是刚需，优先保耳朵清净。

对比：
1. 降噪效果：A主打强降噪，对付地铁轰鸣更拿手；B降噪大概率偏弱，地铁里可能听歌费劲。
2. 佩戴感受：B主打轻便，久戴耳道压迫小；A可能偏重或夹头，40分钟通勤基本能扛，但舒适度不如B。
3. 续航与价格：两款具体续航和价格均未知，但降噪芯片通常更耗电，A续航可能不如B；预算有限的话，需留意A是否溢价过高。

注意：两款具体价格未知，如果A的实际价格远超你的预算，只能退而求其次选B，并在地铁里适当调大音量（伤耳，不建议长期如此）。
```

## 可选 · partial 租户

```text
星河书店支持退货，请通过官方订单页面提交申请，具体结果以审核为准。
```

## 结论

- md = 文案；ChatPromptTemplate = 链上节点；`{var}` 运行时绑定。
- `{{var}}`（loader）与 `{var}`（LC）分阶段用，不要糊在同一段原文里混解析。
- 缺变量要失败可见；改 md 重跑即可，不必改业务管道。
