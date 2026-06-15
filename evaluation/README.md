# Router 评测说明

## 评测范围

当前自动评测聚焦 Router Agent，测试从用户自然语言到结构化分析结果的质量，不访问 MySQL，也不调用 Weather/Ticket Agent。

数据集 `router_cases.json` 的天气城市、日期、铁路线路及出行日期均来自
项目 MySQL 数据库中的真实记录，覆盖：

- 天气查询
- 铁路票务查询
- 天气与票务组合查询
- 缺失参数与追问
- 机票、景点、酒店等未支持请求
- 否定表达和容易误路由的边界请求

## 正式指标

| 指标 | 定义 |
| --- | --- |
| Parse Success Rate | LLM 输出能够成功解析并完成标准化的用例比例 |
| Intent Accuracy | `intent` 与标准答案完全一致的比例 |
| Route Exact Accuracy | `required_agents` 集合与标准答案完全一致的比例 |
| Agent Precision | 正确调用的 Agent 数量 / 所有预测调用的 Agent 数量 |
| Agent Recall | 正确调用的 Agent 数量 / 所有应调用的 Agent 数量 |
| Agent F1 | Agent Precision 与 Recall 的调和平均值 |
| Agent False-positive Case Rate | 至少多调用一个 Agent 的用例比例，越低越好 |
| Unsupported False-call Rate | 未支持请求中仍调用 Weather/Ticket Agent 的比例，越低越好 |
| Slot Value Accuracy | 标准槽位键值被正确提取的比例，等价于 Slot Recall |
| Slot Precision | 模型输出的槽位键值中正确项的比例，多输出错误槽位会降低该指标 |
| Slot Recall | 标准答案中的槽位键值被正确提取的比例 |
| Slot F1 | Slot Precision 与 Slot Recall 的调和平均值 |
| Slot Case Accuracy | 一个用例的所有预期槽位均正确的比例，不惩罚额外槽位 |
| Slot Exact-match Accuracy | 模型槽位字典与标准答案完全一致的用例比例 |
| Extra-slot Case Rate | 至少多输出一个标准答案之外槽位的用例比例，越低越好 |
| Missing-slot Accuracy | `missing_slots` 集合完全正确的比例 |
| Clarification Accuracy | `need_clarification` 判断正确的比例 |
| Overall Case Pass Rate | 解析、意图、路由、槽位、缺失槽位和追问判断全部正确的用例比例 |
| Mean/P50/P95 Latency | Router 分析请求的平均、中位数和 95 分位延迟 |

评测启动时会校验每条标准答案的完整性：每个 Agent 的必填槽位必须全部出现在
`slots` 或 `missing_slots` 中，否则直接终止评测。严格指标会将标准答案之外的额外
槽位视为误提取；`Slot Case Accuracy` 则保留为只观察预期槽位召回情况的宽松指标。

`unsupported` 类按设计只评估不支持意图识别、Agent 路由和追问判断，不参与槽位
Precision、Recall、F1 与完全匹配统计。即使模型提取了问题中的城市，也不会影响该类
用例是否通过。

## 运行方法

确保 Qwen3 vLLM 服务运行后，在项目根目录执行：

```powershell
python -X utf8 -m scripts.evaluate_router
```

常用参数：

```powershell
python -X utf8 -m scripts.evaluate_router --workers 4
python -X utf8 -m scripts.evaluate_router --limit 10
python -X utf8 -m scripts.evaluate_router --dataset evaluation/router_cases.json
```

完整报告默认写入 `.runtime/evaluation/`，该目录不会提交到 Git。

当前 Qwen3-8B-AWQ 的三轮基准结果见 `evaluation/BASELINE.md`。

## 结果使用原则

- 每次修改模型、Prompt 或路由规则后，使用同一数据集重新评测。
- 正式对外数据建议连续运行至少 3 次，并报告平均值。
- 数据集规模变化时，不应直接与旧结果比较。
- 简历中应注明样本数量、模型版本、测试轮数和运行设备。
- 当前指标用于 Router 质量评估，不等同于最终回答事实正确率。
