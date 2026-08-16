# Agent Context Contract

## Scope

本文件用于统一当前 Multi-Agent 需求分析系统中的三类契约：

- Runtime 实际传入 Agent 的信息。
- Stage Artifact 在 Agent 之间传递的信息。
- Prompt 中对输入来源和使用优先级的描述。

本次只做契约审查和统一建议，不修改代码、Prompt、Pipeline 顺序、Context 类型或业务逻辑。

## 1. Current Runtime Facts

### 1.1 `requirement_text` 的真实语义

当前 Workflow State 中保存的 `workflow_state.input.requirement_text` 仍然是原始需求文本，没有被 Context 覆盖。

但在 Agent 调用层，多个 Agent 函数参数仍命名为 `requirement_text`，实际传入内容可能是：

- Text 模式：原始需求文本。
- Markdown 模式：Agent1A 收到 `原始需求 + 原始 Markdown Context`；Agent1B 到 Agent4 收到原始需求和上游 Stage Artifact。
- Structured / Human Compiler / Auto Context 模式：Agent1A、Agent2、Agent3、Agent4 收到 `原始需求 + Agent 专属 Context View`；Agent1B 的 Context View 为空，收到原始需求和 Agent1A Stage Artifact。

因此，当前存在两个层次：

| 名称 | 当前实际含义 | 问题类型 |
|---|---|---|
| `workflow_state.input.requirement_text` | 原始需求文本 | 无冲突 |
| `rendered_agent_input` | 原始需求文本 + 当前 Agent Context View | 正确运行结构 |
| Agent payload 中的 `requirement_text` | 有时是原始需求，有时是 rendered input | 命名和 Prompt 描述冲突 |

结论：运行逻辑没有覆盖原始需求，但 Agent Prompt 和 wrapper 参数名容易让人误解为“只传入原始需求”。这是契约命名问题，不是 Pipeline 行为错误。

### 1.2 当前 Context View 分发

当前 `core/context_tools.py` 中的 Agent Context View 分发如下：

| Agent | 当前 Context sections |
|---|---|
| Agent1A | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns` |
| Agent1B | none |
| Agent2 | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns`, `quality_flags` |
| Agent3 | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns` |
| Agent4 | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns`, `source_refs`, `quality_flags` |

这说明当前已经避免了 Agent1B 再读完整 Context；Agent3 的 `unknowns` 经过前期实验被保留，因为 `risk_items` 只能承接部分 unknown 信息。

## 2. Current Information Flow

```text
Context Source
  -> Context Package
  -> Agent Context View
  -> rendered_agent_input
  -> Agent1A
  -> Agent1A Stage Artifact
  -> Agent1B
  -> Agent1B Stage Artifact
  -> Agent2 + Agent2 Context View
  -> Agent2 Stage Artifact, including legacy risk arrays and risk_items
  -> Agent3 + Agent3 Context View
  -> Agent3 Stage Artifact
  -> Agent4 + Agent4 Context View/source summary
  -> Final Output
```

### 2.1 Stage outputs and downstream consumers

| Stage | 主要输出字段 | 下游消费者 |
|---|---|---|
| Agent1A | `functional_goal`, `user_roles`, `main_flow`, `preconditions`, `edge_cases`, `action_gap_candidates`, `action_context_alignment`, `unassigned_unknowns` | Agent1B, Agent2, Agent3, Agent4 |
| Agent1B | `open_questions`, `question_sources` | Agent2, Agent4 |
| Agent2 | `ambiguity_risks`, `missing_info`, `edge_case_risks`, `permission_risks`, `data_risks`, `performance_risks`, `risk_items` | Agent3, Agent4 |
| Agent3 | `core_test_points`, `edge_test_points`, `performance_test_points`, `acceptance_criteria`, `test_case_drafts` | Agent4 |
| Agent4 | `requirement_summary`, `risk_summary`, `test_recommendation`, `human_review_required`, `critical_open_questions` | Final Output |

## 3. Contract Conflicts

### C1. `requirement_text` 名称与实际输入不一致

代码层为了兼容旧 Agent wrapper，仍用 `requirement_text` 作为 payload key，但 Structured / Auto Context 模式下该字段包含 Agent Context View。

影响：

- Agent1A Prompt 开头仍描述“基于原始需求文本”，但后续 Field Rules 又要求使用 Agent Context View。
- Agent2 Prompt 声明只接收 `requirement_text`、Agent1A 和 Agent1B 结果，没有明确 `requirement_text` 里可能包含 Context View。
- Agent4 Prompt 输入列表没有明确 Context / source summary 的角色。

建议主来源命名：

- `original_requirement_text`：原始需求。
- `agent_context_view`：Agent 专属 Context。
- `rendered_agent_input`：临时组合后的实际 LLM 输入。

### C2. Agent2 Prompt 未同步 Context View 与 `risk_items`

Runtime 中 Agent2 会收到 Agent2 Context View，并且代码在 LLM 输出后后处理生成 `risk_items`。

但 Agent2 Prompt 当前只声明旧六类风险数组，不声明 Context View，也不声明 `risk_items` 的系统生成边界。

影响：

- 从 Prompt 视角看，Agent2 可能只把 Context 当作混入 `requirement_text` 的普通文本。
- `risk_items` 是代码后处理产物，不应要求模型直接生成，但需要在契约文档中明确它属于 Agent2 Stage Artifact。

### C3. Agent4 Runtime 输入多于 Prompt 声明

Agent4 Runtime payload 包含：

- `requirement_text`
- `agent_1_requirement_parsing`
- `agent_1_questions`
- `agent_2_risk_analysis`
- `agent_3_test_design`
- `agent_2_full_output`

Prompt 输入描述没有完整列出 `agent_1_questions` 和 `agent_2_full_output`，但字段规则又要求复用 `agent_1_questions.open_questions`。

影响：

- Prompt 与真实 payload 不完全一致。
- `agent_2_risk_analysis` 与 `agent_2_full_output` 当前传入同一对象，存在重复。

### C4. Agent3 已同步 `risk_items`，但 Context unknowns 仍保留

Agent3 Prompt 已明确 `risk_items` 是结构化风险输入，并要求 unknown 相关验证关注点优先来自 `risk_items.related_unknowns`。

但 Agent3 Context View 仍包含 `unknowns`。这是当前实验后的保守设计：Phase 3 验证显示直接移除 unknowns 会导致部分验证关注点退化。

结论：这是合理重复，不是当前 P0 冲突。后续只有当 Agent2 Stage Artifact 能完整承接 unknown 来源时，才适合继续收窄。

### C5. Markdown 路径仍是 Agent1A 原始压缩模式

Markdown Context 没有 item 级 Context View，当前只在 Agent1A 输入中拼接原始 Markdown；下游只能消费 Agent1A 抽取后的 Stage Artifact。

影响：

- Markdown 信息可能在 Agent1A 压缩时丢失。
- 下游无法稳定获得 item 级 `context_refs`。

结论：这是 Markdown 路径天然限制，不是当前契约错误。Structured / Compiler / Auto Context 是更稳定的 Runtime 路径。

## 4. Duplicate Information Passing

| 信息 | 当前来源 | 是否重复 | 最终主来源 |
|---|---|---|---|
| `business_rules` | Context View；Agent1A `known_conditions`；Agent2 `risk_items.related_rules` | 是，部分合理 | 原始规则以 Context View 为主；解释后的动作级规则以 Agent1A / Agent2 Artifact 为主 |
| `constraints` | Context View；Agent1A `known_conditions`；Agent2 `risk_items.related_constraints` | 是，合理 | Context View 提供原始限制；risk_items 提供风险相关限制 |
| `process_flows` | Context View；Agent1A `main_flow` | 是，合理 | 当前需求流程以 Agent1A `main_flow` 为主；历史流程以 Context View 为补充 |
| `unknowns` | Context View；Agent1A `specific_unknowns` / `unassigned_unknowns`；Agent1B `question_sources`；Agent2 `risk_items.related_unknowns` | 是，阶段化重复 | Agent1A 提供缺口归属；Agent1B 提供澄清问题；Agent2 提供风险化 unknown |
| `risk` | Agent2 旧六类风险数组；Agent2 `risk_items` | 是，兼容性重复 | Agent3 应优先使用 `risk_items`，旧数组保留兼容 |
| `test focus` | Agent3 输出 | 否 | Agent3 Stage Artifact |
| `source_refs` / `context_refs` | Context View；Agent1A/Agent1B/Agent2 Artifact；Trace | 是，合理 | Context View 是原始来源；Stage Artifact 是消费后的来源引用 |

不合理重复：

- Agent4 同时收到 `agent_2_risk_analysis` 和内容相同的 `agent_2_full_output`。
- Agent payload key `requirement_text` 同时承担原始需求和 rendered input 两种语义。

合理重复：

- Agent2 继续消费 Context unknowns，因为其职责是风险识别。
- Agent3 暂时保留 Context unknowns，因为 `risk_items` 还不能完全替代。
- Context refs 在 Trace 和 Stage Artifact 中重复出现，因为它们服务可追溯性。

## 5. Unified Agent Input Protocol

### Agent1A

Input:

- `original_requirement_text`
- Business Context View:
  - `confirmed_facts`
  - `business_rules`
  - `constraints`
  - `process_flows`
  - `unknowns`

Output:

- `functional_goal`
- `user_roles`
- `main_flow`
- `preconditions`
- `edge_cases`
- `action_gap_candidates`
  - `action`
  - `has_gap`
  - `gap_type`
  - `known_conditions`
  - `specific_unknowns`
  - `context_refs`
- `action_context_alignment`
- `unassigned_unknowns`

Contract:

- Context 用于第一次需求理解和动作级缺口归属。
- `unknowns` 只能进入 `specific_unknowns` 或 `unassigned_unknowns`，不能进入已确认事实。
- 已有规则和限制应进入 `known_conditions`，不能被重新概括成宽泛缺口。

### Agent1B

Input:

- `original_requirement_text`
- Agent1A Stage Artifact:
  - `main_flow`
  - `action_gap_candidates`
  - `unassigned_unknowns`

Forbidden:

- 不直接消费 Context View。
- 不重新扫描原始 Context。
- 不绕过 Agent1A 自行生成缺口。

Output:

- `open_questions`
- `question_sources`

Contract:

- 优先把 `specific_unknowns` 转成澄清问题。
- `known_conditions` 已回答的信息不得重复提问。
- `question_sources.context_refs` 保留来源 item ID。

### Agent2

Input:

- `original_requirement_text`
- Agent1A Stage Artifact
- Agent1B Stage Artifact
- Risk Context View:
  - `confirmed_facts`
  - `business_rules`
  - `constraints`
  - `process_flows`
  - `unknowns`
  - `quality_flags`

Output:

- Legacy risk arrays:
  - `ambiguity_risks`
  - `missing_info`
  - `edge_case_risks`
  - `permission_risks`
  - `data_risks`
  - `performance_risks`
- System-built Stage Artifact:
  - `risk_items`

Contract:

- Agent1A/Agent1B Artifact 提供已整理缺口。
- Context View 提供规则、限制、流程、unknown 和质量边界。
- `risk_items` 是 Agent2 阶段提供给 Agent3 的结构化风险接口；当前由代码根据 Agent2 输出、Agent1B `question_sources` 和 Context refs 后处理生成。

### Agent3

Input:

- `original_requirement_text`
- Agent1A Stage Artifact
- Agent2 Stage Artifact:
  - `risk_items`
  - legacy risk arrays
- Business Context View:
  - `confirmed_facts`
  - `business_rules`
  - `constraints`
  - `process_flows`
  - `unknowns`

Priority:

- `risk_items` 是风险相关验证关注点的主输入。
- `related_rules` / `related_constraints` 可作为规则验证依据。
- `related_unknowns` 只能生成待确认或信息不足类关注点，不能当作确定事实。
- Context View 是业务补充和边界校验，不应替代 Agent2 风险判断。

Output:

- `core_test_points`
- `edge_test_points`
- `performance_test_points`
- `acceptance_criteria`
- `test_case_drafts`

Contract:

- Agent3 不负责重新做风险分析。
- Agent3 不应从 Context unknowns 直接扩展确定性测试结论。
- 当前不建议继续移除 `unknowns`，除非 Agent2 Artifact 后续能完整覆盖其验证价值。

### Agent4

Input:

- All Stage Artifacts:
  - Agent1A parsing / gap artifact
  - Agent1B clarification artifact
  - Agent2 risk artifact
  - Agent3 validation artifact
- Source and quality summary:
  - Context refs
  - source summary
  - quality flags

Output:

- `requirement_summary`
- `risk_summary`
- `test_recommendation`
- `human_review_required`
- `critical_open_questions`

Contract:

- Agent4 负责聚合和人工复核判断，不重新分析原始 Context。
- 输出应优先复用 Stage Artifact。
- Context/source summary 只用于来源、质量和复核依据，不用于生成新业务事实。

## 6. Prompt Sync Checklist

### P0: Prompt 与 Runtime 输入描述一致

需要后续同步的 Prompt：

| Prompt | 当前问题 | 建议 |
|---|---|---|
| `prompts/agent1a_parsing_gap_detection.md` | Input 只写 `requirement_text`，但实际可能包含 Agent Context View | 明确输入由 `original_requirement_text` 和可选 `Agent Context View` 组成 |
| `prompts/agent_2_risk_review.md` | 未声明 Agent2 会收到 Context View；Output 未说明 `risk_items` 属于系统后处理 Artifact | 明确 `requirement_text` 中可能包含 Agent2 Context View；说明旧六类风险仍由模型输出，`risk_items` 由系统构建 |
| `prompts/agent_4_summary.md` | 输入列表遗漏 `agent_1_questions`，且未说明 Context/source summary 的使用边界 | 明确优先汇总 Stage Artifact；Context/source summary 只用于来源和复核，不用于重新分析 |

已基本同步的 Prompt：

| Prompt | 状态 | 说明 |
|---|---|---|
| `prompts/agent1b_question_generation.md` | 基本一致 | Agent1B 已不直接消费 Context，主要使用 Agent1A Artifact |
| `prompts/agent_3_test_design.md` | 基本一致 | 已声明 `risk_items` 优先级和 unknown 使用边界 |

遗留 Prompt：

| Prompt | 状态 | 建议 |
|---|---|---|
| `prompts/agent_1_requirement_analysis.md` | 疑似旧路径保留 | 如果仍被入口暴露，应标注 legacy 或同步当前契约 |

### P1: 字段命名统一

建议后续在代码层逐步区分：

- `original_requirement_text`
- `agent_context_view`
- `rendered_agent_input`

不建议一次性改动所有 Agent wrapper，以免破坏已有调用和测试。

### P2: Context View 配置文档化

建议把当前 `AGENT_CONTEXT_SECTIONS` 明确视为 Runtime Contract 配置，并在文档中标注每个 section 的消费者和禁止行为。

不需要新增配置系统。

## 7. Required Code Change Suggestions

### A. Must Change

当前没有必须立即修改的代码。运行路径已经满足：

- 原始 `requirement_text` 未被 Workflow State 覆盖。
- Agent1B 不直接消费 Context。
- Agent3 已明确消费 `risk_items`，且仍保留必要 Context。
- Auto Context 审核门控仍在 Context View 层生效。

真正 P0 是 Prompt/契约描述同步，而不是 Runtime 行为修复。

### B. Later Changes

可以后续修改：

- 将 Agent wrapper 的 `requirement_text` 参数语义拆成 `original_requirement_text` 和 `rendered_agent_input`。
- 在 Agent4 payload 中移除或明确 `agent_2_full_output`，避免与 `agent_2_risk_analysis` 重复。
- 在 Trace 中继续保留 `original_requirement_ref`、`context_view`、`context_consumption`、`final_input_sources`，作为契约验证依据。
- 在 Agent2 代码注释或文档中明确 `risk_items` 是后处理 Stage Artifact。

### C. Not Recommended

当前不建议：

- 移除 Agent3 的 `unknowns` Context View。
- 移除 Agent2 的 Context View。
- 删除旧六类风险数组。
- 让 Agent4 重新读取 Context 生成新的分析结论。
- 新增 Agent、Context 类型、RAG、知识库或动态路由。

## 8. Final Decision

当前五 Agent 架构不需要调整。主要问题不是 Agent 数量或能力不足，而是 Runtime 输入、Prompt 描述和 Stage Artifact 主来源之间的契约表达不完全一致。

推荐统一后的主规则：

- Context 提供原始业务事实、规则、限制、流程、unknown 和来源。
- Stage Artifact 提供 Agent 已处理后的中间结论，包括缺口、问题、风险和验证关注点。
- Prompt 必须说明当前 Agent 应优先消费哪一类输入。
- 同一信息可以在 Context 和 Stage Artifact 中同时存在，但必须明确主来源：
  - 原始依据来自 Context。
  - 阶段判断来自 Stage Artifact。
  - 最终汇总来自 Stage Artifact，而不是重新分析 Context。

