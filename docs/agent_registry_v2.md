# Agent Registry V2

本文档定义当前项目的 Agent Registry 收敛版本。

Registry 只用于架构说明和 Execution Trace 引用，不参与调度，不改变执行逻辑。

## 1. 分类原则

### Agent

Agent 是当前固定 Pipeline 中的执行阶段。

当前 Agent 数量保持 5 个：

- Agent1A: `requirement_gap_detection`
- Agent1B: `clarification`
- Agent2: `risk_analysis`
- Agent3: `controlled_test_draft`
- Agent4: `review`

### Native Capability

Native Capability 是某个 Agent 内部固定承担的阶段职责。

现有 Agent 内部职责统一归为 `native_capabilities`，不再定义为独立 Skill。

### External Skill

External Skill 是外部能力包，必须带来复用、独立替换、专业处理或上下文增强价值。

当前只有一个 External Skill 被受限接入：

```text
understand_domain_repository_context
```

它只通过 Context Provider 被调用，Registry 不参与调度。

### External Skill Candidate

External Skill Candidate 是未来可能接入的能力声明。

当前 candidate 仍不参与执行，例如：

- `github_context`
- `state_transition_analysis`
- `permission_matrix_analysis`
- `historical_defect_retrieval`

### Policy / Workflow Gate

Policy / Workflow Gate 负责限制、阻断、停止生成或决定是否转人工。

以下内容不定义为 Skill：

- `clarification_compression_policy`
- `stop_generation_policy`
- `human_review_routing_policy`
- `evidence_boundary_policy`
- `summary_boundary_policy`

### Tool

Tool 负责确定性处理，例如读取、校验、记录、评估和保存。

当前 Tool：

- `local_markdown_context_reader`
- `execution_trace_writer`
- `future_schema_validator`
- `future_evidence_checker`
- `future_baseline_evaluator`

## 2. Agent Registry 摘要

```json
{
  "agent_id": "requirement_gap_detection",
  "native_capabilities": [
    "requirement_fact_extraction",
    "main_flow_identification",
    "action_gap_detection"
  ],
  "policies": [
    "source_boundary_policy",
    "no_business_assumption_policy"
  ],
  "external_skill_candidates": [
    "prd_markdown_extraction",
    "pdf_table_extraction",
    "github_context",
    "ui_prototype_analysis"
  ],
  "external_skills": [
    "understand_domain_repository_context"
  ],
  "tools": [
    "local_markdown_context_reader",
    "execution_trace_writer"
  ]
}
```

完整声明式配置见：

```text
configs/agent_registry_refs.json
```

## 3. 当前废弃的旧定义

以下说法不再作为当前架构定义：

- 将现有 Agent 内部职责直接拆成独立 Skill。
- 为了架构对称而把固定阶段能力包装成 Skill。
- 将限制、停止生成、转人工等规则包装成 Skill。
- 将确定性校验、运行追踪和基线评估包装成 Skill。
- 声称所有 External Skill 都只停留在 candidate 状态。

收敛后的定义：

```text
现有 Agent 内部能力 = Native Capability
限制与转人工 = Policy / Workflow Gate
确定性处理与记录 = Tool
受限本地仓库上下文增强 = External Skill via Context Provider
未来增强能力 = External Skill Candidate
```

## 4. 当前不做

- 不创建现有 Native Capability 对应的 Skill 文件。
- 不修改 Agent Prompt。
- 不修改 Pipeline 顺序。
- 不增加 Agent 数量。
- 不引入动态路由。
- 不把 Registry 接入调度。
- 不接入远程 GitHub、PDF、表格或第二个 Skill。
