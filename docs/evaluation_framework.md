# Multi-Agent Workflow Evaluation Framework

> 文档状态：历史设计参考。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文不再单独作为项目停止标准。

## 目的

本文定义当前 Multi-Agent Workflow 如何判断是否具备评估条件、如何解释评估结果，以及在修复前如何进行失败分类。

目标是避免继续根据单次失败运行直接修改 Prompt、Context 或代码。推荐流程是：

```text
开发完成
-> Evaluation Readiness
-> Evaluation
-> Failure classification
-> Root cause attribution
-> Action / accept / regression
```

本文不新增 Agent，不改变 Pipeline，不引入 RAG，也不建设评估平台。它只为现有五 Agent Workflow 定义评估规则。

## 核心原则

- 评估准入（Evaluation Readiness）不是模型质量评估。
- Context 质量本身不是目标；只有当它能降低需求分析成本、提高风险识别质量、提升历史经验复用效率时才有价值。
- 自动检查（Automated Check）必须区分确定性检查（deterministic check）和语义判断（semantic judgment）。
- 语义候选信号（semantic candidate）不等于自动失败。
- 语义候选必须经过人工确认后，才能形成失败类型（Failure Type）。
- 冒烟稳定性（Smoke Stability）和正式可靠性（Formal Reliability）是两个不同层级。
- 失败类型（Failure Type）和根因归因（Root Cause Attribution）必须分开存储、分开统计。

## 准入层级

Evaluation Readiness 分为两层。

### 1. 系统评估准入（System Readiness Gate）

System Readiness 是运行级（run-level）的确定性准入。它判断某一次 Evaluation Run 是否具备可执行、可观察、可分析的技术条件。

它检查 Runtime、Contract、Traceability 和 Observability。它不检查模型语义答案是否好。

输出：

```json
{
  "gate": "system_readiness",
  "level": "evaluation_run",
  "result": "pass",
  "blocking": true,
  "failed_checks": [],
  "evidence_refs": []
}
```

结果值：

- `pass`：允许进入本次 Evaluation Run。
- `fail`：阻塞本次 Evaluation Run。

System Readiness 不输出 `review_required`。

### 2. 评估设计准入（Evaluation Design Readiness）

Evaluation Design Readiness 是活动级（campaign-level）的人工批准准入。它判断一组 case、rubric、场景和运行计划是否足以支撑正式 Evaluation Campaign。

它检查 case coverage、rubric completeness、scenario representativeness、human review plan、model comparison plan、repeat-run plan 和 reporting rules。

输出：

```json
{
  "gate": "evaluation_design_readiness",
  "level": "evaluation_campaign",
  "result": "approved",
  "approved_by": "",
  "coverage_gaps": [],
  "rubric_gaps": [],
  "representativeness_notes": []
}
```

结果值：

- `approved`：可以启动正式 Evaluation Campaign。
- `revise_required`：评估设计需要修订。
- `rejected`：当前设计无法支撑有效评估。

该 Gate 由人工批准，不判断某一次模型输出。

## 自动检查契约

所有自动检查统一使用以下契约：

```json
{
  "check_id": "",
  "check_type": "deterministic",
  "result": "pass",
  "severity": "info",
  "evidence_refs": [],
  "notes": ""
}
```

允许的 `check_type`：

- `deterministic`
- `semantic_candidate`

允许的 `result`：

- `pass`
- `fail`
- `review_required`

规则：

- `deterministic` 检查可以输出 `pass` 或 `fail`。
- `semantic_candidate` 检查可以输出 `pass` 或 `review_required`。
- `semantic_candidate` 检查不得输出 `fail`。
- `review_required` 表示需要人工复核的信号，不是已确认失败。

## 人工评估

人工评估用于判断开放式语义质量。评估维度包括：

- 依据性（Grounding）
- 边界遵守（Boundary Compliance）
- 完整性（Completeness）
- 不确定性处理（Uncertainty Handling）
- 相关性（Relevance）
- 有用性（Usefulness）
- 可接受波动（Acceptable Variance）

人工评估不要求唯一 golden answer。它使用：

- `must_cover`
- `valid_optional`
- `unsupported`

## 失败处理流程

```text
Automated deterministic check
-> pass / fail

Automated semantic candidate check
-> pass / review_required
-> human review
-> confirmed_failure / dismissed / acceptable_variance / needs_more_runs
```

只有以下两种情况可以创建已确认的 Failure Type：

- deterministic `fail`
- 人工复核后的 `confirmed_failure`

## 稳定性层级

### 冒烟稳定性（Smoke Stability）

Smoke Stability 是轻量检查，用于发现明显不稳定。

- 推荐运行次数：3 次。
- 用途：发现空输出、schema 漂移、runtime failure、严重行为发散。
- 不用于：正式可靠性结论。
- 输出：`smoke_pass` 或 `smoke_failed`。

### 正式可靠性（Formal Reliability）

Formal Reliability 是正式评估方法。

- 需要多个 case 和多次重复运行。
- 可以包含多个模型。
- 报告 deterministic failure rate、review-required signal rate、human-confirmed failure rate、acceptable variance rate 和 root cause distribution。
- 只有 Formal Reliability 可以支持“某个模型或 Prompt 版本更稳定”这类结论。

## Evaluation Campaign 流程

```text
Evaluation Design Readiness
  -> approved
System Readiness Gate
  -> pass
Evaluation Run
Automated Checks
Human Review
Failure Type classification
Root Cause Attribution
Action decision
Regression Evaluation
```

## 行动决策

在完成 Failure Type classification 和 Root Cause Attribution 后，允许的行动包括：

- fix code
- fix context
- adjust prompt
- change model
- add human review
- accept variance
- improve evaluation method
- defer

不能只因为一个未经人工确认的 semantic candidate 就直接修改系统。
