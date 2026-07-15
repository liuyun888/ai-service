# 04.01 拒答与 Grounding · 实跑记录

- Embedding：`BAAI/bge-small-zh-v1.5`
- Chat：`astron-code-latest`
- **选用 min_score：0.58**
- top_k：4

## 分数探针

| 探针 | top1 | 说明 |
|------|------|------|
| A·库内必有 | 0.8124 | 应正常答，并落到 return_policy.md |
| B·库外离谱 | 0.5625 | 库中无此政策；语义会漂到 shipping_faq，分数中等偏低 → 应拒 |
| C·库内菜单 | 0.6608 | 库内有 cafeteria_menu，分数带作对照（不应被闸门误杀） |
| D·完全无关 | 0.4086 | 更低分对照题；比「月球仓」更干净地落在阈值下方 |

## 闸门结果

### 七天无理由退货需要什么条件？

- refused: `False`
- reason: `passed_gate`
- top1_score: `0.8123660700123901`
- answer: 七天无理由退货需要满足以下条件：
1. 在签收后 **7 个自然日** 内；
2. 商品完好；
3. 配件齐全；
4. 不影响二次销售。

（注：运费由买家承担，具体以订单页规则为准）

source: return_policy.md

### 你们支持月球仓发货吗？保证 10 分钟送达月亮表面吗？

- refused: `True`
- reason: `top1_score=0.5625 < min_score=0.58`
- top1_score: `0.5624598879166548`
- answer: 根据当前知识库资料，我无法确定这一点。你可以换个问法，或补充文档后再问。我不会编造具体数字、条款或承诺。

### 公司股票明年能涨多少？请给出确定收益率。

- refused: `True`
- reason: `top1_score=0.4086 < min_score=0.58`
- top1_score: `0.4085525900975721`
- answer: 根据当前知识库资料，我无法确定这一点。你可以换个问法，或补充文档后再问。我不会编造具体数字、条款或承诺。

## 阈值极端

- 好问 + min_score=0.95 → refused=`True`（误拒演示）
- 坏问 + min_score=0.2 → refused=`False`（滥放演示）

## 结论（自己填）

- 我最终选用的 min_score：`0.58`
- 依据：比「库内题 top1」低一截，比「库外离谱题 top1」高一截。
