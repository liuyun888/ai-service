# writer_agent brief

## 目标

只根据父 Agent 传入的 Top3 JSON 写「退货体验改进草案」大纲；不自行检索全库。

## 完成定义

输出 Markdown 大纲：每条问题 → 动作 → 度量；并在文末标注「依据来自 research JSON」。

## 允许 Tool

- （默认可空）只使用 brief 附件里的 JSON

## 输入附件

父传入：`problems` JSON（research_agent 产出）

## 禁止事项

- 不得编造未出现在 JSON 中的问题
- 不得对用户承诺赔付金额
- 不得再开子 Agent
