# Evaluation Readiness Gate

> 文档状态：历史设计参考。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文不再单独作为项目停止标准。

## 概览

Evaluation Readiness 拆成两个独立 Gate：

1. 系统评估准入（System Readiness Gate）
2. 评估设计准入（Evaluation Design Readiness）

它们回答的是两个不同问题。

| Gate | 层级 | 负责人 | 决策结果 | 阻塞范围 |
|---|---|---|---|---|
| System Readiness Gate | Evaluation Run | 自动确定性检查 | `pass` / `fail` | 单次 run |
| Evaluation Design Readiness | Evaluation Campaign | 人工批准 | `approved` / `revise_required` / `rejected` | 正式 campaign |

## A. 系统评估准入（System Readiness Gate）

### 目的

System Readiness 用于验证当前 run 是否具备被评估的技术条件。

它不判断 semantic quality。

### 输入

- pipeline config
- run config
- context package
- context view
- prompt version
- model config
- trace 或 dry-run trace
- schema definitions
- stage contract definitions

### 确定性检查

| 检查项 | 通过条件 | 失败含义 |
|---|---|---|
| Pipeline 可执行 | Pipeline 能启动并到达终态 | Runtime 不具备评估条件 |
| Agent 顺序 | Agent1A -> Agent1B -> Agent2 -> Agent3 -> Agent4 | Workflow 顺序无效 |
| Context 路由 | Context 进入预期 Agent Context View | Context routing 断裂 |
| Stage Artifact 传递 | 下游能看到所需上游 artifact | Contract propagation 断裂 |
| Trace 完整性 | workflow events 和 agent traces 被保存 | Run 不可观察 |
| raw / normalized 分离 | 能区分 raw output 和 normalized output | 无法审计 Normalizer 影响 |
| 必填 schema 字段 | normalized output 中存在 required fields | Contract 不满足 |
| context_refs 格式 | 引用已知 context item ID；无 context 时允许为空 | 来源追踪无效 |
| API / 网络隔离 | infrastructure failure 能与 model output 区分 | 评估会混淆 Runtime 与模型质量 |

### 输出

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

### 规则

- `pass` 允许进入本次 Evaluation Run。
- `fail` 阻塞本次 Evaluation Run。
- System Readiness 永远不返回 `review_required`。
- System Readiness 不检查 risk、question 或 validation point 的语义质量。
- System Readiness 失败不是模型质量失败。

## B. 评估设计准入（Evaluation Design Readiness）

### 目的

Evaluation Design Readiness 用于验证评估活动设计是否公平、完整、具有代表性，是否足以启动正式 Evaluation Campaign。

它必须由人工批准。

### 输入

- evaluation case set
- case coverage matrix
- scenario taxonomy
- rubric
- expected focus files
- human review plan
- model comparison plan
- repeat-run plan
- failure type taxonomy
- root cause taxonomy

### 检查项

| 检查项 | 期望条件 |
|---|---|
| Case coverage | cases 覆盖目标场景类型 |
| Rubric completeness | 覆盖 Grounding、Boundary、Completeness、Uncertainty、Relevance、Usefulness、Variance |
| Expected focus structure | 定义 `must_cover`、`valid_optional`、`unsupported` |
| Scenario representativeness | cases 能代表真实产品/测试分析工作 |
| Context coverage | 根据需要覆盖无 Context、有用 Context、unknown Context、无关 Context、冲突/过期 Context |
| Human review plan | 评审者知道哪些内容必须人工判断 |
| Automated metric boundary | semantic candidate 不被当成自动失败 |
| Repeat-run plan | Smoke Stability 与 Formal Reliability 分开 |
| Reporting plan | Failure Type 和 Root Cause 分开存储、分开统计 |

### 输出

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

### 规则

- `approved` 允许启动正式 Evaluation Campaign。
- `revise_required` 表示需要补充 case、rubric 或覆盖范围。
- `rejected` 表示当前设计无法支撑有意义的评估。
- Evaluation Design Readiness 不判断任何单次 run output。

## 不属于 Gate 条件的内容

以下内容不能单独阻塞 Readiness：

- 某个 risk item 看起来价值偏低。
- 某个 question 表达不够自然。
- 某个 validation point 不完整。
- 两个合理模型输出的表述不同。
- 某个 semantic candidate 暗示可能存在无依据推理。

这些属于 evaluation finding 或 review candidate，不是 readiness failure。
