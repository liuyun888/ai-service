# Embedding 相似度实跑记录
- provider: `local`
- model: `BAAI/bge-small-zh-v1.5`
- dim: **512**
- vec0_head: `[-0.04843, 0.06884, 0.00324, -0.00626, -0.01211, -0.04934, -0.00645, 0.04964]`

## 文本
1. 降噪耳机续航多久
2. 这款耳机电池能用几小时
3. 明天食堂吃什么

## 余弦相似度
- sim(1,2) 同义续航 = **0.7084**
- sim(1,3) 无关食堂 = **0.1222**

结论：同义句明显高于无关句 → Embedding 几何距离可用。

> 写入 Milvus 前确认 Collection 维度与本 dim 一致（本仓库 `scripts/00_05_init_milvus.py` 默认 1024；若用 bge-small-zh-v1.5 为 512，需改 DIM 或换模型）。
