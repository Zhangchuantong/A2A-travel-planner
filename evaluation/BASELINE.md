# Qwen3-8B-AWQ Router 基准

## 测试配置

| 项目 | 配置 |
| --- | --- |
| 测试日期 | 2026-06-15 |
| 模型 | `Qwen/Qwen3-8B-AWQ` |
| 推理框架 | vLLM |
| 数据集 | `evaluation/router_cases.json` |
| 用例数量 | 30 |
| 测试轮数 | 3 |
| 每轮并发数 | 4 |
| Thinking 模式 | 关闭 |

本基准只评测 Router 的意图分析、Agent 选择、槽位抽取和追问判断，不包含 MySQL、A2A Agent 调用和最终答案生成。

## 三轮结果

| 指标 | 三轮平均 | 结果范围 |
| --- | ---: | ---: |
| Parse Success Rate | 100.00% | 100.00% - 100.00% |
| Intent Accuracy | 90.00% | 90.00% - 90.00% |
| Route Exact Accuracy | 90.00% | 90.00% - 90.00% |
| Agent Precision | 90.91% | 90.91% - 90.91% |
| Agent Recall | 100.00% | 100.00% - 100.00% |
| Agent F1 | 95.24% | 95.24% - 95.24% |
| Agent False-positive Case Rate | 10.00% | 10.00% - 10.00% |
| Unsupported False-call Rate | 0.00% | 0.00% - 0.00% |
| Slot Value Accuracy / Recall | 98.53% | 98.53% - 98.53% |
| Slot Precision | 98.53% | 98.53% - 98.53% |
| Slot F1 | 98.53% | 98.53% - 98.53% |
| Slot Case Accuracy | 96.15% | 96.15% - 96.15% |
| Slot Exact-match Accuracy | 92.31% | 92.31% - 92.31% |
| Extra-slot Case Rate | 3.85% | 3.85% - 3.85% |
| Missing-slot Accuracy | 83.33% | 83.33% - 83.33% |
| Clarification Accuracy | 83.33% | 83.33% - 83.33% |
| Overall Case Pass Rate | 83.33% | 83.33% - 83.33% |

## 延迟

| 指标 | 三轮平均 | 结果范围 |
| --- | ---: | ---: |
| Mean | 2.443s | 2.437s - 2.450s |
| P50 | 2.368s | 2.354s - 2.382s |
| P95 | 3.205s | 3.170s - 3.239s |
| Max | 3.228s | 3.182s - 3.255s |

## 已知问题

三轮评测中持续出现的主要问题：

- 否定表达未被路由规则正确识别，例如“不用查票”“不要查天气”。
- 部分铁路票务请求中的日期会被模型漏提取。
- 天气请求缺少城市时，模型可能无依据补充默认城市。

## 简历表述建议

可以写：

> 基于 MySQL 真实天气和车票数据构建 30 条 Router 评测集；Qwen3-8B-AWQ 在 3 轮测试中取得 90.00% 路由完全匹配准确率、95.24% Agent F1、98.53% 槽位 F1 和 92.31% 槽位严格匹配率，Router 分析 P95 延迟约 3.21 秒。

需要同时说明该结果来自自建小规模测试集，不能代表通用旅行场景效果。
