# Evaluation Failure Taxonomy

> 文档状态：历史设计参考。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文不再单独作为项目停止标准。

## 目的

本文将失败类型（Failure Type）和根因归因（Root Cause Attribution）明确分开。

Failure Type 描述观察到了什么问题。

Root Cause Attribution 描述这个问题为什么可能发生。

二者必须分开存储、分开统计。

## 失败类型（Failure Type）

只有以下情况可以创建 Failure Type：

- deterministic 自动检查失败；
- 人工评审确认某个 semantic candidate 是失败。

semantic candidate 在评审前不是失败。

### Failure Type 记录

```json
{
  "failure_id": "",
  "failure_type": "contract_failure",
  "confirmed_by": "deterministic_check",
  "source_signal_ids": [],
  "evidence_refs": [],
  "notes": ""
}
```

### Failure Type 分类

| Failure Type | 含义 | 典型确认方式 |
|---|---|---|
| `runtime_failure` | Pipeline、API、网络、文件或依赖问题导致无法有效评估 | deterministic |
| `contract_failure` | required schema、Stage Artifact 或字段契约被违反 | deterministic |
| `grounding_failure` | 输出包含 requirement、context 或 artifact 不支持的业务事实 | human review |
| `boundary_failure` | Agent 执行了职责边界之外的工作 | human review |
| `completeness_failure` | 输出遗漏 rubric 中的 must-cover item | human review |
| `uncertainty_handling_failure` | unknown 被当成 confirmed fact | human review 或 deterministic candidate 加人工复核 |
| `traceability_failure` | 必要来源或 context reference 缺失、无效 | 引用格式无效时 deterministic；语义来源不清时 human review |
| `stability_failure` | 重复运行出现不可接受的结构性或已确认语义不稳定 | formal reliability review |

## 根因归因（Root Cause Attribution）

Root Cause 在 Failure Type 被确认之后再判断。不得从 Failure Type 直接推导 Root Cause。

### Root Cause 记录

```json
{
  "root_cause_id": "",
  "failure_id": "",
  "root_cause": "prompt",
  "confidence": "medium",
  "evidence_refs": [],
  "notes": ""
}
```

### Root Cause 分类

| Root Cause | 含义 |
|---|---|
| `runtime` | API、网络、依赖、文件或执行环境问题 |
| `context_source` | 来源内容缺失、过期、无关或冲突 |
| `context_compiler` | Human Context Compiler 或 context preparation 错误转换了信息 |
| `context_view` | Context 被分发给错误 Agent，或分发过多/过少 |
| `stage_contract` | 上游 Stage Artifact 不足以支撑下游 Agent |
| `normalizer_validator` | 代码归一化或校验修改、丢失或未能约束 contract 字段 |
| `prompt_instruction` | Prompt 指令不清晰、冲突或过期 |
| `model_capability` | 模型不具备所需推理能力 |
| `model_variance` | 多次运行存在预期范围内的模型波动 |
| `evaluation_method` | case、rubric 或自动指标本身有问题 |

## 候选信号（Candidate Signal）

Candidate signal 是自动语义检查发现的疑似问题。

它不计入失败。

```json
{
  "signal_id": "",
  "check_id": "",
  "signal_type": "possible_unknown_as_fact",
  "result": "review_required",
  "evidence_refs": [],
  "notes": ""
}
```

人工评审后的允许结果：

- `confirmed_failure`
- `dismissed`
- `acceptable_variance`
- `needs_more_runs`

只有 `confirmed_failure` 会创建 Failure Type。

## 统计口径

统计必须分开报告。

Failure Type 统计：

```json
{
  "contract_failure": 0,
  "grounding_failure": 0,
  "boundary_failure": 0,
  "completeness_failure": 0,
  "uncertainty_handling_failure": 0,
  "traceability_failure": 0,
  "stability_failure": 0
}
```

Root Cause 统计：

```json
{
  "runtime": 0,
  "context_source": 0,
  "context_compiler": 0,
  "context_view": 0,
  "stage_contract": 0,
  "normalizer_validator": 0,
  "prompt_instruction": 0,
  "model_capability": 0,
  "model_variance": 0,
  "evaluation_method": 0
}
```

Candidate signal 统计：

```json
{
  "review_required": 0,
  "confirmed_failure": 0,
  "dismissed": 0,
  "acceptable_variance": 0,
  "needs_more_runs": 0
}
```

不要合并这三类统计。

## 行动决策

Root Cause Attribution 完成后，选择一个行动：

- fix code
- fix context
- adjust prompt
- change model
- add human review
- accept variance
- improve evaluation method
- defer

不能只因为 semantic candidate 出现就直接采取修复行动。
