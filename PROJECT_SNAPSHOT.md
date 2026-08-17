# Project Snapshot

> 文档状态：Historical / Superseded。
>
> 历史快照说明：本文生成于 2026-08-08，记录的是当时项目状态。
>
> 当前项目已完成 Project Exit 并冻结，最终状态、运行方式和结项结论请以 `README.md` 与 `docs/project_exit_report.md` 为准。本文保留为历史审计材料，不作为当前最终口径。
>
> 2026-08-17 合同收敛说明：`requirement_text` 兼容命名、original requirement / rendered input 区分，以及 Agent1B indirect-only Context visibility 已在 `docs/agent_context_contract.md` 澄清。本文第 7 节的相关条目保留为历史发现，不再作为新的待扩展范围。

- 生成时间：2026-08-08
- 项目路径：`E:\AI-Research\project2_multi_agent`
- 依据范围：当前代码、Prompt、配置、文档、测试数据、已有输出与 trace
- 说明：本文只记录当前真实状态。代码与文档不一致时，以当前代码和配置为准；无法确认处标记为“未知”。

## 1. 项目定位

### 项目解决什么问题

该项目是一个面向“需求分析 / 测试设计”的 Multi-Agent 工作流实验项目。

项目关注的问题是：当原始需求存在缺失、模糊、隐含规则或边界不清时，单个大模型容易直接补全业务事实、生成看似完整但不可验证的风险分析和测试用例。当前系统通过分阶段 Agent 链路，将需求解析、缺口识别、澄清问题、风险分析、受控测试设计和最终汇总分离，降低跨阶段职责混淆，并保留执行 trace 供人工审查。

### 当前目标

当前目标是验证一个受控的需求到测试设计工作流是否能：

- 从原始需求中提取可确认事实和主流程。
- 显式识别需求缺口和未知项。
- 将缺口转化为澄清问题。
- 基于上游缺口和证据生成风险分析。
- 在信息不足时生成受控测试设计，而不是伪完整测试用例。
- 输出可追踪的最终汇总，并标记是否需要人工审查。
- 通过 trace / workflow state / context package 保留执行过程。

### 明确非目标

根据当前 README、项目定义和架构文档，当前非目标包括：

- 不做生产级测试管理平台。
- 不做完整企业级需求管理系统。
- 不做自动动态路由。
- 不做多模型自动协作调度。
- 不做自动业务决策。
- 不做行业知识库或通用 RAG 系统。
- 不直接接入远程 GitHub / PDF 表格 / UI 原型等外部来源作为已实现能力。
- 不把 registry 作为执行调度器。
- 不让 Agent 自主选择 Skill 或 Tool。
- 不在信息不足时生成完整、确定性的测试用例。

### 当前阶段

当前阶段：MVP / 实验验证阶段。

证据：

- README 和 `docs/project_definition_v1.md` 将项目定义为 demo / MVP 范围。
- 存在本地验证脚本、评估脚本、对比实验输出和 trace。
- 当前没有发现生产部署配置、CI 配置或正式服务化入口。
- `configs/pipeline_config.json` 当前默认关闭扩展能力：
  - `use_agent1_two_stage`: `false`
  - `use_agent2_dual_channel`: `false`
  - `use_harness_run_manager`: `false`
  - `context_sources`: `[]`

## 2. 当前整体架构

### 系统流程图

```text
输入需求文本 / Markdown / 测试 case
        |
        v
加载 pipeline_config.json
        |
        v
初始化 Workflow State 与 Execution Trace
        |
        v
加载 Context Sources
        |
        +-- 无 Context / 非结构化 Markdown
        |        |
        |        v
        |   仅 Agent1A 可接收追加后的原始文本
        |
        +-- Context Package V2
                 |
                 v
          按 Agent 构造专属 Context View
        |
        v
Agent1A Requirement Parsing + Gap Detection
        |
        v
Agent1B Clarification Question Generation
        |
        v
Agent2 Risk Analysis
        |
        v
Agent3 Controlled Test Draft
        |
        v
Agent4 Result Summary
        |
        v
输出 final_result / agent outputs / workflow state / trace files
```

### Agent列表

- Agent1A：Requirement Parsing + Gap Detection
- Agent1B：Clarification Question Generation
- Agent2：Risk Analysis
- Agent3：Controlled Test Draft
- Agent4：Result Summary

当前固定执行顺序定义在 `core/pipeline_runner.py`：

```text
agent1a -> agent1b -> agent2 -> agent3 -> agent4
```

### Agent职责与数据流

#### Agent1A：requirement_gap_detection

- 输入：
  - 原始需求文本。
  - 在结构化 context 模式下，接收 Agent1A 专属 Context View。
  - 在 Markdown context 模式下，接收追加后的上下文文本。
- 处理：
  - 提取功能目标、用户角色、主流程、前置条件、边界情况。
  - 按主流程动作识别是否存在需求缺口。
  - 为每个动作输出 `action_gap_candidates`。
  - 在结构化 Context V2 下，运行后会被代码层做 `align_action_gap_candidates_with_context` 对齐。
- 输出：
  - `functional_goal`
  - `user_roles`
  - `main_flow`
  - `preconditions`
  - `edge_cases`
  - `action_gap_candidates`
  - 可选：`action_context_alignment`
  - 可选：`unassigned_unknowns`
- 依赖：
  - Prompt：`prompts/agent1a_parsing_gap_detection.md`
  - 实现：`core/agent1a_parsing_gap_detection.py`
  - LLM 客户端：`core/llm_client.py`
  - 可选 Context：`core/context_tools.py`
- 限制：
  - 不允许基于经验补全业务事实。
  - 不生成澄清问题。
  - 不生成风险分析。
  - 不生成测试建议。
  - 只依据原始需求和 Context View。

#### Agent1B：clarification

- 输入：
  - 原始需求文本。
  - Agent1A 的 `main_flow`。
  - Agent1A 的 `action_gap_candidates`。
  - Agent1A 的 `unassigned_unknowns`。
- 处理：
  - 将 Agent1A 的具体未知项转化为澄清问题。
  - 当前实现中，如果存在 `specific_unknowns`，代码会按未知项构造问题来源，优先于模型输出。
- 输出：
  - `open_questions`
  - `question_sources`
- 依赖：
  - Prompt：`prompts/agent1b_question_generation.md`
  - 实现：`core/agent1b_question_generation.py`
- 限制：
  - 不补充新规则、新字段、新功能、新异常。
  - 不重新判断 gap_type。
  - 不提出解决方案。
  - 不生成测试点。
  - 当前代码中的 `AGENT_CONTEXT_SECTIONS` 对 Agent1B 配置为空，因此 Agent1B 不直接读取完整 Context View。

#### Agent2：risk_analysis

- 输入：
  - 需求文本。
  - Agent1A 输出。
  - Agent1B 输出。
  - 结构化 context 模式下，接收 Agent2 专属 Context View。
- 处理：
  - 生成 legacy 风险数组。
  - 代码层基于 Agent1B 的 `question_sources`、Agent1A 的 gap candidates 和 legacy risks 构造 `risk_items`。
- 输出：
  - `ambiguity_risks`
  - `missing_info`
  - `edge_case_risks`
  - `permission_risks`
  - `data_risks`
  - `performance_risks`
  - `risk_items`
- 依赖：
  - Prompt：`prompts/agent_2_risk_review.md`
  - 实现：`core/agent2_risk_analysis.py`
- 限制：
  - 不生成测试用例。
  - 不提出解决方案。
  - 不添加未在输入中出现的业务事实。
  - 不输出通用 checklist。

#### Agent3：controlled_test_draft

- 输入：
  - 需求文本。
  - Agent1A 输出。
  - Agent2 输出。
  - 结构化 context 模式下，接收 Agent3 专属 Context View。
- 处理：
  - 生成测试关注点、验收标准和受控测试草稿。
  - 当信息不足时，输出“信息不足 / 需补充”的测试草稿，而不是完整测试用例。
- 输出：
  - `core_test_points`
  - `edge_test_points`
  - `performance_test_points`
  - `acceptance_criteria`
  - `test_case_drafts`
- 依赖：
  - Prompt：`prompts/agent_3_test_design.md`
  - 实现：`core/agent3_test_design.py`
- 限制：
  - 不在缺少业务规则时生成完整测试用例。
  - 不补全流程、规则、异常、权限、性能指标。
  - 不使用 `related_unknowns` 作为已确认事实。

#### Agent4：review

- 输入：
  - 需求文本。
  - Agent1A 输出。
  - Agent1B 输出。
  - Agent2 输出。
  - Agent3 输出。
  - 结构化 context 模式下，接收 Agent4 专属 Context View。
- 处理：
  - 汇总上游结果。
  - 判断是否需要人工审查。
  - 复用 Agent1B 的开放问题作为关键开放问题。
- 输出：
  - `requirement_summary`
  - `risk_summary`
  - `test_recommendation`
  - `human_review_required`
  - `critical_open_questions`
- 依赖：
  - Prompt：`prompts/agent_4_summary.md`
  - 实现：`core/agent4_result_summary.py`
- 限制：
  - 不重新分析需求。
  - 不新增风险。
  - 不新增测试方向。
  - 不新增业务事实。
  - `critical_open_questions` 应直接来自 Agent1B 的 `open_questions`。

## 3. Workflow定义

### 当前完整执行链

```text
Input
↓
Load Config
↓
Initialize Workflow State
↓
Load Context Sources
↓
Build Agent Context View
↓
Agent1A Requirement Parsing + Gap Detection
↓
Agent1B Clarification Question Generation
↓
Agent2 Risk Analysis
↓
Agent3 Controlled Test Draft
↓
Agent4 Result Summary
↓
Persist Result + Trace
```

### Input

- 为什么存在：
  - 工作流需要一个原始需求作为唯一主输入。
- 上游输入：
  - JSON case、Markdown inbox 文件、验证脚本内置输入或评估数据。
- 下游用途：
  - 传给所有 Agent，作为事实边界。
- 当前实现方式：
  - `main.py` 从 `data/test_cases` 读取 JSON。
  - `run_requirement_inbox.py` 从 `data/requirements_inbox` 读取 Markdown。
  - `verify_workflow.py` 支持 text / markdown / repository / structured / auto-context。
  - `evaluate_context_comparison.py` 使用 `data/evaluation_cases`。

### Load Config

- 为什么存在：
  - 控制运行模式、扩展开关和 context source。
- 上游输入：
  - `configs/pipeline_config.json`
- 下游用途：
  - 决定是否启用 Agent1 two-stage 扩展和 context source。
- 当前实现方式：
  - `core/pipeline_runner.py` 读取配置对象。
  - 当前默认 `context_sources` 为空。

### Initialize Workflow State

- 为什么存在：
  - 记录阶段状态、输入、context、错误和人工审查状态。
- 上游输入：
  - run_id、requirement_text、stage_order、context_sources。
- 下游用途：
  - 所有阶段写入状态。
  - 出错时标记 failed / skipped。
- 当前实现方式：
  - `core/workflow_state.py`
  - Workflow 状态枚举：pending / running / completed / failed / stopped。
  - Stage 状态枚举：pending / running / success / failed / skipped。

### Load Context Sources

- 为什么存在：
  - 支持把外部已确认上下文纳入 Agent 输入。
- 上游输入：
  - config 或 case 中的 `context_sources`。
- 下游用途：
  - 生成 context item。
  - 失败时 required context 会阻断工作流。
- 当前实现方式：
  - `core/context_tools.py`
  - 支持：
    - `local_markdown`
    - `local_structured_context`
    - `local_repository`
  - 不支持远程 GitHub、PDF、UI 原型、网络抓取作为当前已实现运行能力。

### Build Agent Context View

- 为什么存在：
  - 避免所有 Agent 接收相同上下文。
  - 控制每个 Agent 可见的信息类型。
- 上游输入：
  - Context Package V2。
- 下游用途：
  - 生成每个 Agent 的 `rendered_agent_input`。
- 当前实现方式：
  - `core/context_tools.py`
  - 当前代码配置：
    - Agent1A：confirmed_facts, business_rules, constraints, process_flows, unknowns
    - Agent1B：空
    - Agent2：confirmed_facts, business_rules, constraints, process_flows, unknowns, quality_flags
    - Agent3：confirmed_facts, business_rules, constraints, process_flows, unknowns
    - Agent4：confirmed_facts, business_rules, constraints, process_flows, unknowns, source_refs, quality_flags

### Agent1A Stage

- 为什么存在：
  - 将需求事实和缺口识别从后续问题、风险、测试生成中分离。
- 上游输入：
  - 原始需求。
  - 可选 Agent1A Context View。
- 下游用途：
  - Agent1B 生成澄清问题。
  - Agent2 生成风险。
  - Agent3 生成测试草稿。
  - Agent4 汇总。
- 当前实现方式：
  - `core/agent1a_parsing_gap_detection.py`
  - Prompt-only LLM 输出 + Python 归一化。
  - 结构化 context 下会执行 action gap 与 unknown 的对齐。

### Agent1B Stage

- 为什么存在：
  - 将缺口转成可供人工确认的问题。
- 上游输入：
  - Agent1A 的主流程、缺口候选和未知项。
- 下游用途：
  - Agent2 使用问题来源生成 missing info / risk_items。
  - Agent4 输出 critical_open_questions。
- 当前实现方式：
  - `core/agent1b_question_generation.py`
  - LLM 调用后有代码层归一化。
  - 若 `specific_unknowns` 存在，代码直接构造问题来源。

### Agent2 Stage

- 为什么存在：
  - 将不完整需求导致的风险显式化。
- 上游输入：
  - 原始需求、Agent1A、Agent1B。
- 下游用途：
  - Agent3 使用 risk_items 控制测试设计。
  - Agent4 汇总风险。
- 当前实现方式：
  - `core/agent2_risk_analysis.py`
  - LLM 输出 legacy 风险数组。
  - Python 后处理生成 `risk_items`。

### Agent3 Stage

- 为什么存在：
  - 生成测试关注点，同时避免在缺少业务规则时生成伪完整测试用例。
- 上游输入：
  - 原始需求、Agent1A、Agent2。
- 下游用途：
  - Agent4 生成测试建议汇总。
- 当前实现方式：
  - `core/agent3_test_design.py`
  - Prompt 要求输出 JSON。
  - 代码只解析 JSON，未做复杂归一化。

### Agent4 Stage

- 为什么存在：
  - 给人工审查者一个汇总结果。
- 上游输入：
  - 原始需求、Agent1A、Agent1B、Agent2、Agent3。
- 下游用途：
  - 最终输出。
- 当前实现方式：
  - `core/agent4_result_summary.py`
  - Prompt 要求只汇总，不重新分析。

### Persist Result + Trace

- 为什么存在：
  - 保留可审查执行记录。
- 上游输入：
  - 每个阶段输出、workflow state、tool trace。
- 下游用途：
  - 人工复盘、评估、架构评审。
- 当前实现方式：
  - `outputs/...`
  - `outputs/traces/{run_id}/workflow_events.jsonl`
  - `outputs/traces/{run_id}/agent_traces.jsonl`
  - `outputs/traces/{run_id}/tool_traces.jsonl`

## 4. Agent Registry / Skill / Schema

## Agent Registry

Registry 文件：`configs/agent_registry_refs.json`

Registry 当前性质：

- `registry_version`: `v2`
- `scope`: `execution_trace_reference_only`
- 只作为架构审查和 trace 引用。
- 不参与调度。
- 不决定执行顺序。
- 不替代代码实现。

### requirement_gap_detection

- agent_id：`requirement_gap_detection`
- stage：`requirement_gap_detection`
- prompt引用：`prompts/agent1a_parsing_gap_detection.md`
- implementation引用：`core/agent1a_parsing_gap_detection.py`
- input contract：
  - 原始需求文本。
  - 可选 Agent1A Context View。
- output contract：
  - `requirement_gap_detection_schema`
- forbidden behavior：
  - 不补全业务事实。
  - 不生成澄清问题。
  - 不生成风险。
  - 不生成测试建议。

### clarification

- agent_id：`clarification`
- stage：`clarification`
- prompt引用：`prompts/agent1b_question_generation.md`
- implementation引用：`core/agent1b_question_generation.py`
- input contract：
  - 原始需求文本。
  - Agent1A main_flow。
  - Agent1A action_gap_candidates。
  - Agent1A unassigned_unknowns。
- output contract：
  - `clarification_schema`
- forbidden behavior：
  - 不新增业务事实。
  - 不提出解决方案。
  - 不重新判断缺口类型。
  - 不生成测试内容。

### risk_analysis

- agent_id：`risk_analysis`
- stage：`risk_analysis`
- prompt引用：`prompts/agent_2_risk_review.md`
- implementation引用：`core/agent2_risk_analysis.py`
- input contract：
  - 原始需求文本。
  - Agent1A 输出。
  - Agent1B 输出。
  - 可选 Agent2 Context View。
- output contract：
  - `risk_analysis_schema`
- forbidden behavior：
  - 不新增业务事实。
  - 不生成测试用例。
  - 不提供解决方案。
  - 不输出通用 checklist。

### controlled_test_draft

- agent_id：`controlled_test_draft`
- stage：`controlled_test_draft`
- prompt引用：`prompts/agent_3_test_design.md`
- implementation引用：`core/agent3_test_design.py`
- input contract：
  - 原始需求文本。
  - Agent1A 输出。
  - Agent2 输出。
  - 可选 Agent3 Context View。
- output contract：
  - `controlled_test_draft_schema`
- forbidden behavior：
  - 不生成完整测试用例。
  - 不补全业务规则。
  - 不把未知项当成事实。

### review

- agent_id：`review`
- stage：`review`
- prompt引用：`prompts/agent_4_summary.md`
- implementation引用：`core/agent4_result_summary.py`
- input contract：
  - 原始需求文本。
  - Agent1A 输出。
  - Agent1B 输出。
  - Agent2 输出。
  - Agent3 输出。
  - 可选 Agent4 Context View。
- output contract：
  - `review_schema`
- forbidden behavior：
  - 不重新分析。
  - 不新增风险。
  - 不新增测试方向。
  - 不修改、合并、扩展 Agent1B 的关键问题。

## Skill

### understand_domain_repository_context

- skill名称：`understand_domain_repository_context`
- 作用：
  - 从本地仓库提取文件树、入口点、签名和元数据，并作为 repository context package 进入 trace / context。
- 被哪个Agent使用：
  - Registry 中声明为 Agent1A、Agent2、Agent3、Agent4 的 external skill。
  - 实际运行中作为 context provider，不由 Agent 自主调用。
- 当前是否实际调用：
  - 是，作为 `local_repository` context source 的 provider。
  - 已有 smoke trace：`outputs/traces/smoke_adapter_repo_success_58abcf42/tool_traces.jsonl`
- 实现引用：
  - `core/repository_context_skill_adapter.py`
  - 外部本地脚本：`C:\Users\12643\.codex\skills\understand-domain\extract-domain-context.py`
- 限制：
  - 本地只读。
  - 不执行 shell。
  - 不访问网络。
  - 不调用完整 `/understand` 流程。
  - 只允许项目根目录内路径。

### Candidate-only Skills

以下 Skill 在 registry 中仅作为候选能力列出，当前未参与执行：

- `prd_markdown_extraction`
- `pdf_table_extraction`
- `github_context`
- `ui_prototype_analysis`
- `state_transition_analysis`
- `permission_matrix_analysis`
- `api_contract_testing`
- `historical_defect_retrieval`

当前是否实际调用：否。

## Schema

当前项目没有发现独立 JSON Schema 文件。Schema 主要由 Prompt 输出要求、Python 归一化逻辑、registry 引用名和文档共同约束。

### requirement_gap_detection_schema

- 用途：
  - Agent1A 输出需求解析和缺口识别结果。
- 字段说明：
  - `functional_goal`：功能目标。
  - `user_roles`：用户角色列表。
  - `main_flow`：主流程动作列表。
  - `preconditions`：前置条件列表。
  - `edge_cases`：边界情况列表。
  - `action_gap_candidates`：按动作记录的缺口候选。
  - `action_gap_candidates[].action`：对应主流程动作。
  - `action_gap_candidates[].has_gap`：是否存在缺口。
  - `action_gap_candidates[].gap_type`：`flow` / `rule` / `scope` / `input_output` / 空字符串。
  - `action_gap_candidates[].known_conditions`：已知条件。
  - `action_gap_candidates[].specific_unknowns`：具体未知项。
  - `action_gap_candidates[].context_refs`：上下文引用。
  - `action_context_alignment`：结构化 context 对齐结果，代码后处理生成。
  - `unassigned_unknowns`：无法分配到动作的 unknown，代码后处理生成。

### clarification_schema

- 用途：
  - Agent1B 输出澄清问题。
- 字段说明：
  - `open_questions`：开放问题列表。
  - `question_sources`：问题来源列表。
  - `question_sources[].question`：问题文本。
  - `question_sources[].source_type`：来源类型，当前可由 specific_unknown / unassigned_unknown 等生成。
  - `question_sources[].action`：关联动作。
  - `question_sources[].gap_type`：缺口类型。
  - `question_sources[].specific_unknown`：对应未知项。
  - `question_sources[].context_refs`：上下文引用。

### risk_analysis_schema

- 用途：
  - Agent2 输出风险分析。
- 字段说明：
  - `ambiguity_risks`：歧义风险。
  - `missing_info`：缺失信息。
  - `edge_case_risks`：边界情况风险。
  - `permission_risks`：权限风险。
  - `data_risks`：数据风险。
  - `performance_risks`：性能风险。
  - `risk_items`：代码后处理生成的结构化风险项。
  - `risk_items[].risk_id`：风险 ID。
  - `risk_items[].risk_type`：风险类型。
  - `risk_items[].description`：风险描述。
  - `risk_items[].related_unknowns`：关联未知项。
  - `risk_items[].related_rules`：关联规则。
  - `risk_items[].related_constraints`：关联限制。
  - `risk_items[].context_refs`：上下文引用。

### controlled_test_draft_schema

- 用途：
  - Agent3 输出受控测试设计。
- 字段说明：
  - `core_test_points`：核心测试关注点。
  - `edge_test_points`：边界测试关注点。
  - `performance_test_points`：性能测试关注点。
  - `acceptance_criteria`：验收标准。
  - `test_case_drafts`：测试草稿，不等同完整测试用例。

### review_schema

- 用途：
  - Agent4 输出最终汇总。
- 字段说明：
  - `requirement_summary`：需求汇总。
  - `risk_summary`：风险汇总。
  - `test_recommendation`：测试建议汇总。
  - `human_review_required`：是否需要人工审查。
  - `critical_open_questions`：关键开放问题，要求来自 Agent1B。

### workflow_state_schema

- 用途：
  - 记录工作流状态和阶段状态。
- 字段说明：
  - `run_id`：运行 ID。
  - `input.requirement_text`：原始需求文本。
  - `input.context_sources`：上下文来源配置。
  - `context.items`：加载成功或失败的上下文条目。
  - `stages.agent1a` 到 `stages.agent4`：各阶段状态、输出和错误。
  - `control.current_stage`：当前阶段。
  - `control.status`：工作流状态。
  - `control.stop_reason`：停止原因。
  - `control.human_review_required`：人工审查标记。
  - `errors`：错误列表。

### context_package_v2_schema

- 用途：
  - 为 Agent 提供结构化、可追踪上下文。
- 字段说明：
  - `context_package_version`：必须为 `v2`。
  - `structured_content.confirmed_facts`：确认事实。
  - `structured_content.business_rules`：业务规则。
  - `structured_content.constraints`：限制条件。
  - `structured_content.process_flows`：流程信息。
  - `structured_content.unknowns`：未确认事项。
  - `structured_content.source_refs`：来源引用。
  - `structured_content.quality_flags`：质量标记。
  - 每个 item 通常包含 `id`、`text`、`source_ref`、`confidence`、`applies_to` 等字段。

### execution_trace_schema

- 用途：
  - 记录 workflow、agent、tool / skill 执行事件。
- 字段说明：
  - workflow events：`event_type`、`run_id`、`stage`、`status`、`timestamp` 等。
  - agent traces：`trace_id`、`run_id`、`case_id`、`agent_id`、`stage`、`registry_ref`、`input_sources`、`output_snapshot`、`execution_status`、`human_review` 等。
  - tool traces：`trace_id`、`run_id`、`case_id`、`tool_id`、`capability_type`、`input_refs`、`output_ref`、`output_snapshot`、`execution_status`、`error` 等。

## 5. 当前实际运行案例

### Case：requirement inbox phone_login real

- Input：
  - 文件：`data/requirements_inbox/phone_login.md`
  - 运行目录：`outputs/requirement_runs/inbox_phone_login_real_20260808_103229_277737`
  - context_sources：空
- Agent执行过程：
  - Agent1A 提取手机号登录目标、5 个主流程动作和若干具体未知项。
  - Agent1B 生成 8 个开放问题。
  - Agent2 生成风险项。
  - Agent3 输出测试关注点，并在测试草稿中说明信息不足。
  - Agent4 汇总并标记需要人工审查。
- 关键输出：
  - `main_flow_count`: 5
  - `question_count`: 8
  - `risk_item_count`: 10
  - `core_test_points`: 4
  - `edge_test_points`: 8
  - `test_case_drafts`: 1
  - `critical_open_questions`: 8
  - `human_review_required`: true
- 最终结果：
  - workflow completed。
  - 需要人工审查。
- 是否成功：
  - 执行成功。
- 问题：
  - Agent1B 输出中仍出现了示例化表达，例如“如长度、前缀”“如短信验证码”，与 Prompt 中“不补充示例 / 不提出具体实现”的限制存在偏差。
  - Agent1A 对部分实现细节边界仍偏宽。

### Case：evaluation case_01_complete_requirement

- Input：
  - 文件：`data/evaluation_cases/case_01_complete_requirement.json`
  - 运行目录：`outputs/evaluation_runs/case_01_complete_requirement`
  - context_sources：空
- Agent执行过程：
  - Text-only real 模式执行完整 Agent 链。
  - Agent1A 解析完整邮箱绑定需求。
  - Agent1B 基于缺口输出澄清问题。
  - Agent2 生成风险。
  - Agent3 生成测试设计。
  - Agent4 汇总。
- 关键输出：
  - 具体数值见该目录下 `agent*_output.json` 与 `final_result.json`。
  - `docs/workflow_evaluation_report.md` 记录该案例暴露出 Agent1A 边界偏宽问题。
- 最终结果：
  - workflow completed。
- 是否成功：
  - 执行成功。
- 问题：
  - 完整需求下，Agent1A 仍可能把实现细节视为未知项。
  - Agent2 会继承并放大上游宽泛未知项。

### Case：evaluation case_02_incomplete_requirement

- Input：
  - 文件：`data/evaluation_cases/case_02_incomplete_requirement.json`
  - 运行目录：`outputs/evaluation_runs/case_02_incomplete_requirement`
  - context_sources：空
- Agent执行过程：
  - Text-only real 模式执行完整 Agent 链。
  - 该案例用于验证不完整手机号登录需求的缺口识别、澄清问题、风险和测试草稿。
- 关键输出：
  - 具体输出见对应目录。
  - context comparison 中 text-only、structured context、compiler context 三种版本的 specific_unknown 数均为 8。
- 最终结果：
  - workflow completed。
- 是否成功：
  - 执行成功。
- 问题：
  - 缺口数量在有无 context 下未减少，但结构化 context 能增加 context_refs 和规则关联。

### Case：evaluation case_03_complex_rule_requirement

- Input：
  - 文件：`data/evaluation_cases/case_03_complex_rule_requirement.json`
  - 运行目录：`outputs/evaluation_runs/case_03_complex_rule_requirement`
  - context_sources：空
- Agent执行过程：
  - Text-only real 模式执行完整 Agent 链。
  - 用于验证复杂优惠券规则下的缺口、风险和测试设计传递。
- 关键输出：
  - context comparison 中三种版本的 specific_unknown 数均为 3。
  - P0 后 compiler context 版本中 assigned_alignment 为 3，unassigned 为 0。
- 最终结果：
  - workflow completed。
- 是否成功：
  - 执行成功。
- 问题：
  - 结构化 context 增加规则关联，但 risk item 数量不一定减少。

### Case：context comparison A/B/C

- Input：
  - 脚本：`evaluate_context_comparison.py`
  - 数据：`data/evaluation_cases`
  - 输出：`outputs/context_comparison`
- Agent执行过程：
  - 对每个评估 case 执行三个版本：
    - A_text_only：无 context。
    - B_structured_context：手写 Context Package V2。
    - C_compiler_context：由 Human Context Markdown 编译生成 Context Package V2。
- 关键输出：
  - case01：
    - A specific_unknown 7，risk_items 19。
    - B specific_unknown 4，risk_items 17。
    - C specific_unknown 2，risk_items 10。
  - case02：
    - A/B/C specific_unknown 均为 8。
    - B/C 增加 context_refs。
  - case03：
    - A/B/C specific_unknown 均为 3。
    - B/C 增加来源和动作分配。
- 最终结果：
  - 三种版本均完成。
- 是否成功：
  - 执行成功。
- 问题：
  - Context 的价值依赖结构化、可追踪、与 action 绑定。
  - 纯 Markdown context 会被 Agent1A 压缩，后续阶段 item-level trace 不稳定。

### Case：context comparison P0 after applies_to

- Input：
  - 输出：`outputs/context_comparison_p0/summary_metrics.json`
- Agent执行过程：
  - 对 compiler context 的 `applies_to` 支持进行 P0 验证。
- 关键输出：
  - case01：
    - specific_unknown 2
    - unassigned 0
    - assigned_alignment 2
    - agent1a_context_ref 2
    - risk_items 17
  - case02：
    - specific_unknown 8
    - unassigned 0
    - assigned_alignment 8
    - agent1a_context_ref 8
    - risk_items 8
  - case03：
    - specific_unknown 3
    - unassigned 0
    - assigned_alignment 3
    - agent1a_context_ref 3
    - risk_items 10
- 最终结果：
  - applies_to/action alignment 生效。
- 是否成功：
  - 执行成功。
- 问题：
  - P0 解决的是 unknown 与 action 对齐问题，不等于完整解决上下文价值、风险数量或输出边界问题。

### Case：repository context adapter smoke

- Input：
  - trace：`outputs/traces/smoke_adapter_repo_success_58abcf42/tool_traces.jsonl`
  - context type：`local_repository`
- Agent执行过程：
  - 该案例验证本地 repository context skill adapter。
  - 未确认该 trace 是否执行完整 Agent 链；已确认 tool trace 成功。
- 关键输出：
  - `tool_id`: `understand_domain_repository_context`
  - `capability_type`: `skill`
  - `content_type`: `repository_context_json`
  - `execution_status.status`: `success`
- 最终结果：
  - repository context package 生成成功。
- 是否成功：
  - Skill / context provider 执行成功。
- 问题：
  - 该能力仅提供本地 repository context，不代表远程 GitHub 或完整 understand 流程已接入。

### Case：inbox example fake

- Input：
  - 输出目录：`outputs/requirement_runs/inbox_example_fake_20260808_102043_302954`
  - agent mode：fake
- Agent执行过程：
  - 使用 fake Agent 模块执行结构验证。
- 关键输出：
  - 输出中包含 `__fake_agent_output__` 和 `fake_mode_notice`。
- 最终结果：
  - workflow completed。
- 是否成功：
  - 执行成功。
- 问题：
  - 只能验证链路结构，不能用于判断模型输出质量。

## 6. 已知问题和历史调整

### 问题：Agent 会根据经验补全业务事实

- 调整：
  - 在 Agent1 / Agent2 / Agent3 / Agent4 Prompt 中加入事实边界和禁止补全约束。
  - 引入 Agent1A 缺口识别。
  - 输出 unknown / open_questions / risk_items，而不是直接补齐业务规则。
- 当前状态：
  - 已缓解。
  - 真实输出中仍存在边界偏宽和示例化表达。

### 问题：单阶段 Agent1 同时解析需求和生成问题，职责不稳定

- 调整：
  - 当前主链路拆分为 Agent1A 和 Agent1B。
  - Agent1A 负责解析和缺口识别。
  - Agent1B 负责澄清问题生成。
- 当前状态：
  - 当前 `core/pipeline_runner.py` 默认使用 Agent1A + Agent1B。
  - 旧 Agent1 保留在 `core/agent1_requirement_parsing.py`。

### 问题：风险分析容易变成通用 checklist

- 调整：
  - Agent2 Prompt 限制不输出通用 checklist。
  - 代码层基于 Agent1B question_sources 和 Agent1A gap candidates 构造 `risk_items`。
- 当前状态：
  - 已形成结构化风险链路。
  - 上游缺口偏宽时，Agent2 仍会继承并放大。

### 问题：测试设计容易输出伪完整测试用例

- 调整：
  - Agent3 输出从完整测试用例收敛为 controlled test draft。
  - Prompt 要求信息不足时停止生成完整用例。
- 当前状态：
  - 真实案例中可看到 Agent3 输出“信息不足 / 需补充”式草稿。

### 问题：最终汇总可能重新分析或扩展

- 调整：
  - Agent4 Prompt 限制只汇总上游输出。
  - 要求 `critical_open_questions` 直接来自 Agent1B。
- 当前状态：
  - 已缓解。
  - 文档中仍记录最终输出 source/context 追踪不稳定的问题。

### 问题：缺少执行状态和 trace

- 调整：
  - 增加 `core/workflow_state.py`。
  - 增加 `core/execution_trace.py`。
  - 输出 workflow events、agent traces、tool traces。
- 当前状态：
  - 已实现。
  - Trace 只记录，不参与调度、校验或重试。

### 问题：Context 直接塞入 Prompt 后容易被压缩或丢失来源

- 调整：
  - 引入 Context Package V2。
  - 引入 Agent Context View。
  - 引入 context compiler 和 auto context preparer。
  - 引入 `applies_to` 用于 unknown 与 action 对齐。
- 当前状态：
  - 结构化 V2 路径已实现。
  - Markdown context 路径仍是 Agent1A raw compression 模式。
  - Agent1B 当前不直接消费完整 Context View。

### 问题：外部 Skill 边界不清

- 调整：
  - `agent_registry_v2` 明确区分 native capability、tool、external skill、candidate skill。
  - 仅接入本地只读 repository context skill adapter。
- 当前状态：
  - `understand_domain_repository_context` 已实现为 context provider。
  - 其他 external skills 仍是 candidate_only。

## 7. 当前未解决问题

- Agent1A 在完整需求下仍可能把实现细节或非必要细节识别为未知项。
- Agent1B 真实输出中仍可能出现示例化问题表达，与 Prompt 限制不完全一致。
- Agent2 会继承并放大 Agent1A / Agent1B 的上游边界问题。
- Agent3 / Agent4 输出中的 source/context 引用仍不稳定，尤其在 Markdown context 路径下。
- Agent2 / Agent3 的结构化输出没有统一强制携带 item-level `context_refs`。
- 历史发现：`requirement_text` 在部分运行时实际可能是“原始需求 + Context View”的 rendered input，字段命名与真实含义存在不一致；当前已在 `docs/agent_context_contract.md` 澄清为兼容命名问题。
- Agent4 runtime payload 中包含 `agent_2_risk_analysis` 和 `agent_2_full_output`，二者当前为重复对象。
- 历史发现：部分文档曾写 Agent1B 消费 context sections，但当前代码中 Agent1B sections 为空；当前已在 `docs/agent_context_contract.md` 澄清为 Agent1B indirect-only Context visibility。
- `docs/context_layer_boundary.md` 等早期文档描述“未实现 Context Layer”，与当前代码中的 Context V2 / compiler / preparer 状态不一致。
- `extensions/agent2_dual_channel/agent2_risk_dual.py` 引用的 Prompt 路径下未发现对应 Prompt 文件；该扩展当前默认关闭。
- `extensions/agent1_two_stage/agent1_parsing.py` 和 `extensions/harness/run_manager.py` 当前为空文件。
- Human Context Model V1 文档存在，但当前未发现完整三类 Human Context Runtime 实现；已实现的是 context compiler / Context Package V2 路径。
- Auto Context 当前是本地规则 / 关键词式候选生成与人工审核流程，不是语义 RAG 或自动确认机制。
- 当前未发现 CI 配置。
- 当前未发现正式单元测试框架配置；主要验证方式是脚本和已有输出。
- 当前目录不是 git repo，无法基于 git 历史确认变更来源。
- 当前生产部署状态：未知。

## 8. 当前项目文件结构

```text
project2_multi_agent/
├─ .env                                      [配置文件，内容未展开]
├─ README.md                                 [文档文件]
├─ main.py                                   [核心入口：批量 harness]
├─ run_requirement_inbox.py                  [核心入口：真实 Markdown 需求入口]
├─ verify_workflow.py                        [测试/验证脚本]
├─ evaluate_context_comparison.py            [测试/评估脚本]
├─ prepare_context.py                        [Context 准备 CLI]
├─ compile_context.py                        [Context 编译 CLI]
├─ app/
│  └─ main.py                                [旧入口/示例入口]
├─ config/
│  └─ settings.py                            [配置文件，legacy LLM 设置]
├─ configs/
│  ├─ pipeline_config.json                   [核心配置]
│  └─ agent_registry_refs.json               [核心配置：registry/trace 引用]
├─ core/
│  ├─ agent1_requirement_parsing.py          [旧 Agent1 实现]
│  ├─ agent1a_parsing_gap_detection.py       [核心 Agent1A 实现]
│  ├─ agent1b_question_generation.py         [核心 Agent1B 实现]
│  ├─ agent2_risk_analysis.py                [核心 Agent2 实现]
│  ├─ agent3_test_design.py                  [核心 Agent3 实现]
│  ├─ agent4_result_summary.py               [核心 Agent4 实现]
│  ├─ context_compiler.py                    [核心 Context compiler]
│  ├─ context_preparer.py                    [核心 Auto Context preparer]
│  ├─ context_tools.py                       [核心 Context provider/view]
│  ├─ execution_trace.py                     [核心 Trace]
│  ├─ llm_client.py                          [核心 LLM client]
│  ├─ pipeline_runner.py                     [核心 Workflow runner]
│  ├─ repository_context_skill_adapter.py    [核心 Skill adapter]
│  └─ workflow_state.py                      [核心 Workflow state]
├─ data/
│  ├─ case/                                  [测试数据]
│  ├─ cases/                                 [测试数据]
│  ├─ evaluation_cases/                      [评估测试数据]
│  ├─ expected_behavior_baseline/            [评估基线数据]
│  ├─ history/                               [Context 历史资料]
│  ├─ human_context/                         [人工 Context Markdown]
│  ├─ prepared_context/                      [准备后的 Context 中间产物]
│  ├─ requirements_inbox/                    [真实需求输入]
│  └─ test_cases/                            [harness 测试 case]
├─ docs/
│  ├─ agent_context_contract.md              [文档：Agent Context Contract]
│  ├─ agent_registry_v2.md                   [文档：Agent Registry]
│  ├─ context_layer_boundary.md              [文档：早期 Context 边界]
│  ├─ context_package_v2_design.md           [文档：Context Package V2]
│  ├─ context_value_evaluation.md            [文档：Context 对比结论]
│  ├─ execution_trace_phase1.md              [文档：Trace 设计]
│  ├─ expected_behavior_baseline.md          [文档：预期行为基线]
│  ├─ external_skill_repository_context.md   [文档：Repository Skill 边界]
│  ├─ failure_mode_analysis.md               [文档：失败模式]
│  ├─ human_context_model_v1_spec.md         [文档：Human Context Model]
│  ├─ information_flow_analysis.md           [文档：信息流分析]
│  ├─ project_definition_v1.md               [文档：项目定义]
│  ├─ requirement_inbox.md                   [文档：真实需求入口]
│  ├─ system_architecture_review.md          [文档：架构审查]
│  └─ workflow_state_v1.md                   [文档：Workflow State]
├─ extensions/
│  ├─ agent1_two_stage/
│  │  ├─ agent1_parsing.py                   [扩展文件，当前为空]
│  │  └─ agent1_question_decision.py         [扩展实现，默认关闭]
│  ├─ agent2_dual_channel/
│  │  └─ agent2_risk_dual.py                 [扩展实现，默认关闭]
│  └─ harness/
│     ├─ case_loader.py                      [harness 工具]
│     ├─ result_saver.py                     [harness 工具]
│     └─ run_manager.py                      [扩展文件，当前为空]
├─ outputs/
│  ├─ context_comparison/                    [运行输出]
│  ├─ context_comparison_p0/                 [运行输出]
│  ├─ evaluation_runs/                       [运行输出]
│  ├─ requirement_runs/                      [运行输出]
│  ├─ traces/                                [运行输出：workflow/agent/tool traces]
│  └─ verify_runs/                           [运行输出]
├─ prompts/
│  ├─ agent_1_requirement_analysis.md        [Prompt：旧 Agent1]
│  ├─ agent1a_parsing_gap_detection.md       [Prompt：Agent1A]
│  ├─ agent1b_question_generation.md         [Prompt：Agent1B]
│  ├─ agent_2_risk_review.md                 [Prompt：Agent2]
│  ├─ agent_3_test_design.md                 [Prompt：Agent3]
│  ├─ agent_4_summary.md                     [Prompt：Agent4]
│  └─ extensions/
│     └─ agent1_two_stage/
│        └─ prompts/
│           └─ agent1_question_decision.md   [Prompt：Agent1 扩展]
├─ services/
│  └─ llm_client.py                          [旧 LLM client]
├─ workflows/
│  └─ run_pipeline.py                        [旧 4-Agent workflow]
├─ .understand-anything/                     [生成/分析产物]
├─ .idea/                                    [IDE 文件]
├─ __pycache__/                              [运行缓存]
├─ run_agent1a_parsing_and_gap_detection/    [空目录]
├─ run_agent1b_question_generation/          [空目录]
└─ 总结文档/                                  [文档/总结资料]
```
