# Agent 能力分类收敛

本文档用于收敛当前项目中的 Agent 能力定义。

当前结论：

> 现有 5 个执行 Agent 的内部能力不再定义为独立 Skill，而统一归为 `native_capabilities`。

Skill 在本项目中的定义是：

> 可被 Agent 按任务需要调用的外部可复用能力包，能够带来复用、解耦、按条件选择、独立替换或专业能力扩展。

因此，不能仅因为某项能力可以被拆分，就将其定义为 Skill。

## 1. 当前 5 个 Agent 的 Native Capabilities

### Agent1A: requirement_gap_detection

- **实现文件**：`core/agent1a_parsing_gap_detection.py`
- **Prompt**：`prompts/agent1a_parsing_gap_detection.md`
- **native_capabilities**：
  - `requirement_fact_extraction`
  - `main_flow_identification`
  - `action_gap_detection`
  - `action_gap_candidate_normalization`
- **说明**：这些能力固定服务于 Agent1A 阶段，目前没有跨 Agent 复用、动态选择或独立替换需求。

### Agent1B: clarification

- **实现文件**：`core/agent1b_question_generation.py`
- **Prompt**：`prompts/agent1b_question_generation.md`
- **native_capabilities**：
  - `clarification_question_generation`
- **policies**：
  - `clarification_compression_policy`
- **说明**：澄清问题生成是 Agent1B 的核心职责；问题数量控制和去重属于 Policy，不定义为 Skill。

### Agent2: risk_analysis

- **实现文件**：`core/agent2_risk_analysis.py`
- **Prompt**：`prompts/agent_2_risk_review.md`
- **native_capabilities**：
  - `missing_information_mapping`
  - `evidence_bound_risk_classification`
- **policies**：
  - `evidence_boundary_policy`
- **说明**：风险分析当前只由 Agent2 固定执行，暂不抽象为 Skill。未来如果多个 Workflow 复用风险分类能力，可再升级为 External Skill 或独立可版本化能力。

### Agent3: controlled_test_draft

- **实现文件**：`core/agent3_test_design.py`
- **Prompt**：`prompts/agent_3_test_design.md`
- **native_capabilities**：
  - `controlled_test_draft_generation`
  - `acceptance_criteria_extraction`
- **policies**：
  - `stop_generation_policy`
- **说明**：测试草案生成是 Agent3 的阶段职责；信息不足时停止完整生成属于 Workflow Gate / Policy，不定义为 Skill。

### Agent4: review

- **实现文件**：`core/agent4_result_summary.py`
- **Prompt**：`prompts/agent_4_summary.md`
- **native_capabilities**：
  - `traceable_result_summary`
- **policies**：
  - `human_review_routing_policy`
  - `summary_boundary_policy`
- **说明**：结果汇总是 Agent4 的固定阶段职责；是否需要人工复核属于 Workflow Gate / Policy，不定义为 Skill。

## 2. 重新分类结果

| 原候选能力 | 当前分类 | 说明 |
|---|---|---|
| Requirement Fact Extraction | Native Capability | Agent1A 阶段职责 |
| Requirement Gap Detection | Native Capability | Agent1A 阶段职责，未来可评估是否独立化 |
| Clarification Question Generation | Native Capability | Agent1B 阶段职责 |
| Clarification Compression | Policy | 数量控制和去重规则，不是外部可复用能力包 |
| Missing Information Mapping | Native Capability | Agent2 内部字段映射和风险输入整理 |
| Evidence-Bound Risk Classification | Native Capability | Agent2 阶段职责，未来可独立评估 |
| Controlled Test Draft | Native Capability | Agent3 阶段职责 |
| Stop Generation Control | Workflow Gate / Policy | 控制是否允许完整生成，不是 Skill |
| Traceable Result Summary | Native Capability | Agent4 阶段职责 |
| Human Review Routing | Workflow Gate / Policy | 控制是否转人工，不是 Skill |
| Schema Validation | Tool | 确定性结构校验 |
| Evidence Check | Tool | 确定性证据边界检查 |
| Execution Trace | Tool | 运行过程记录 |
| Baseline Evaluation | Tool | 行为边界评估 |

## 3. External Skill Candidates

当前项目最值得未来接入的 Skill，不是现有 Agent 内部能力，而是补充上下文的外部能力。

| candidate | 解决的问题 | 可消费 Agent | 触发条件 | 优先级 |
|---|---|---|---|---|
| `prd_markdown_extraction` | 从 PRD/Markdown 提取需求背景、规则、流程 | Agent1A, Agent2, Agent3 | 输入包含 PRD 或 Markdown 文档 | P0 |
| `pdf_table_extraction` | 从 PDF/表格中提取需求上下文 | Agent1A, Agent2, Agent3 | 输入包含 PDF、Excel、表格 | P0 |
| `github_context` | 从 GitHub Issue、README、PR 中获取项目上下文 | Agent1A, Agent2, Agent4 | 输入包含 GitHub 链接或仓库信息 | P1 |
| `ui_prototype_analysis` | 从截图或原型图提取页面、字段、交互信息 | Agent1A, Agent3 | 输入包含截图或原型图 | P1 |
| `state_transition_analysis` | 分析状态流转和缺失状态 | Agent2, Agent3 | 需求存在明显状态流 | P1 |
| `permission_matrix_analysis` | 分析多角色权限边界 | Agent2, Agent3 | 需求存在多角色或权限边界 | P1 |
| `api_contract_testing` | 基于接口契约生成测试关注点 | Agent3 | 输入包含 OpenAPI 或接口文档 | P2 |
| `historical_defect_retrieval` | 检索历史缺陷和测试资产 | Agent2, Agent3, Agent4 | 输入包含缺陷库或测试资产来源 | P2 |

这些候选能力仅作为未来接入方向，不参与当前执行。

## 4. 当前不做的事情

- 不创建现有 Native Capability 对应的 Skill 文件。
- 不把 Registry 接入运行调度。
- 不实现 External Skill。
- 不增加 Agent 数量。
- 不修改 Pipeline 顺序。
- 不把 Policy 或 Tool 包装成 Skill。

## 5. 收敛后的判断

现有 Agent 内部能力以 `native_capabilities` 描述即可。真正值得 Skill 化的是未来从外部来源接入、用于补充上下文或提供专业分析方法的能力。

当前阶段的重点是：

```text
Agent Registry 显式边界
+ Execution Trace 记录执行
+ Policy / Tool 分类清晰
+ External Skill Candidate 预留位置
```

而不是把现有 Agent 拆成更多 Skill。
