# 03.05 相似度检索 · 三问 topK 对比

- 样例目录：`/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/samples/docs`
- 索引后端：**memory**
- Embedding：`BAAI/bge-small-zh-v1.5`
- top_k：**4**

## Step 1 · Index

- 文档数：5，总块数：**25**

- `cafeteria_menu.md`：5 chunks
- `course_enrollment.md`：5 chunks
- `hospital_visit.md`：5 chunks
- `return_policy.md`：5 chunks
- `shipping_faq.md`：5 chunks

## Q1 · 七天无理由退货需要什么条件？

期望 top1：`return_policy.md`

- #1 0.8124  return_policy.md  chunk 2  [七天无理由退货] ## 七天无理由退货  签收后 **7 个自然日** 内，商品完好、配件齐全、不影响二次销售， 可申请无理由退货。运费由买家承担，具体以订单页规则为准。
- #2 0.6433  hospital_visit.md  chunk 4  [退费说明] ## 退费说明  未做的检查项目可在 7 个工作日内到收费窗口申请退费，需出示缴费凭证。
- #3 0.5921  return_policy.md  chunk 3  [质量问题换货] ## 质量问题换货  签收超过 7 日后，若出现非人为质量问题，凭购买凭证申请换货或维修。 需提供订单号与故障描述。
- #4 0.5520  shipping_faq.md  chunk 4  [签收与验货] ## 签收与验货  请当面验货后再签收。若外包装明显破损，可拒收并联系客服处理。

## Q2 · 订单一般几天能发货？

期望 top1：`shipping_faq.md`

- #1 0.7723  shipping_faq.md  chunk 1  [发货时效] ## 发货时效  工作日 **16:00 前** 付款的订单，当日发出；16:00 后付款的订单，次工作日发出。 大促期间可能延迟 1～2 个工作日，以订单页公告为准。
- #2 0.6592  return_policy.md  chunk 2  [七天无理由退货] ## 七天无理由退货  签收后 **7 个自然日** 内，商品完好、配件齐全、不影响二次销售， 可申请无理由退货。运费由买家承担，具体以订单页规则为准。
- #3 0.6217  shipping_faq.md  chunk 3  [物流查询] ## 物流查询  发货后可在「我的订单 → 物流详情」查看运单号；也可复制单号到快递公司官网查询。
- #4 0.5559  shipping_faq.md  chunk 2  [配送范围] ## 配送范围  默认快递覆盖全国（港澳台及偏远地区除外）。新疆、西藏等偏远地区时效可能增加 2～4 天。

## Q3 · 选修数据结构需要先修哪些课？

期望 top1：`course_enrollment.md`

- #1 0.7892  course_enrollment.md  chunk 1  [先修课程] ## 先修课程  选修 **数据结构（CS201）** 前，须已通过： - 程序设计基础（CS101） - 离散数学（MATH110）  未满足先修条件将无法在教务系统选课。
- #2 0.7538  course_enrollment.md  chunk 0  # 数据结构 · 选课说明
- #3 0.6309  course_enrollment.md  chunk 4  [教材] ## 教材  主教材：《数据结构与算法分析》第 3 版；实验手册见课程平台下载。
- #4 0.5096  course_enrollment.md  chunk 3  [考核方式] ## 考核方式  平时作业 30%、期中项目 30%、期末考试 40%。缺勤超过 1/3 总课时不得参加期末考。

## topK 对比（同一问：七天无理由退货）

- **K=2**：块少，Prompt 短，但可能漏召回
- **K=5**：召回更全，但噪声块也可能进 Prompt

## 结论（参考答案）

- Retrieve = 问题向量化 + 与库中块算相似度 + 取 topK。
- 相关文档应排在前面；无关文档（如食堂菜单）不应在业务问题下霸榜。
- 本跑使用索引后端：**memory**（memory=内存，milvus=03.04 入库后）。
