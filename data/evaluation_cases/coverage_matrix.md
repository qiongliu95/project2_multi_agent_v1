# Evaluation Case Coverage Matrix

> 文档状态：Evaluation Design 输入材料。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文只说明 case 覆盖范围，不直接给出模型质量结论。

## 目的

本文用于支撑评估设计准入（Evaluation Design Readiness）。它说明当前 evaluation cases 覆盖了哪些场景，以及在启动正式 Evaluation Campaign 前还缺少哪些覆盖。

它不是模型质量报告。

## 当前 Cases

| case_id | scenario_type | must_cover | valid_optional | unsupported | required_context_condition | expected_human_review_points |
|---|---|---|---|---|---|---|
| case_01_complete_requirement | complete_requirement | 主流程、已知规则、少量 unknown、有限风险 | 少量合理的实践性验证关注点 | 编造重试次数、无关登录/安全机制 | Text-only baseline；Structured / Compiler Context 可用于对比 | 系统是否过度生成 unknown 或低价值风险 |
| case_02_incomplete_requirement | incomplete_requirement | specific unknowns、具体 clarification questions、missing info 到 risk 的映射 | 额外相关边界场景 | 编造验证方式、有效期、失败次数、锁定时间、日志字段 | Text-only baseline；Structured / Compiler Context 可测试已知规则是否减少宽泛 gap | questions 是否可回答，risks 是否有依据 |
| case_03_complex_rule_requirement | complex_rule_requirement | 复杂业务规则、constraints、unknowns、基于规则的 validation focus | 从规则派生出的额外边界场景 | 编造叠加规则、编造展示优先级、错误扣减运费 | Structured / Compiler Context 对验证 Context View 行为有价值 | Agent3 是否使用规则，同时不把 unknown 写成确定标准 |

## 覆盖状态

| 场景 | 当前覆盖 | Readiness 影响 |
|---|---|---|
| 完整需求 | case_01 已覆盖 | 足以支持 smoke 和有限评估 |
| 信息不足需求 | case_02 已覆盖 | 足以支持 smoke 和有限评估 |
| 复杂规则需求 | case_03 已覆盖 | 足以支持 smoke 和有限评估 |
| 分支 / 异常流程 | 未明确覆盖 | 正式 campaign 前的缺口 |
| Context unknown | 通过复杂 case 部分覆盖 | 正式 campaign 前需要显式 case |
| Context 部分解决 unknown | 未明确覆盖 | 正式 campaign 前的缺口 |
| 无关 Context | evaluation cases 未覆盖 | 正式 campaign 前的缺口 |
| 冲突 / 过期 Context | evaluation cases 未覆盖 | 正式 campaign 前的缺口 |

## Evaluation Design Readiness 决策

当前 case set 适合：

- development smoke validation
- context comparison baseline
- prompt / contract regression checks

当前 case set 还不足以支持：

- formal reliability claims
- model-to-model quality ranking
- production readiness claims

正式 Evaluation Campaign 前，需要新增或批准覆盖以下场景的 cases：

- branch and exception flow
- context unknown
- context partially resolving unknown
- irrelevant context
- conflict or deprecated context

## 报告规则

本矩阵只用于支持 campaign design approval。它不能单独用于声明模型输出质量。
