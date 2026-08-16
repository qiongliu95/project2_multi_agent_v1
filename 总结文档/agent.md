基于独立职责、输入输出契约和真实调用路径，共提取出 **6 个 Agent 能力**：5 个现行 Agent，1 个兼容实验 Agent。

## 1. 需求事实与动作缺口分析 Agent

**解决的问题**：从不完整需求中提取事实，并防止模型通过常识补全缺失规则。

**输入**：`requirement_text`。

**核心处理逻辑**：提取目标、角色、动作和已知条件；遍历全部动作；按 `flow/rule/scope/input_output` 判断主要缺口；生成动作级中间状态。

**输出**：`functional_goal`、`user_roles`、`main_flow`、`preconditions`、`edge_cases`、`action_gap_candidates`。

**边界**：只能使用原文信息；不生成澄清问题；不设计产品方案；每个动作只保留一个主要缺口类型。

**适用场景**：需求预分析、测试分析前置、流程完整性检查。

**不适用场景**：需要结合业务知识库、页面原型或历史系统规则判断的场景。

**项目证据**：[处理规则](E:/AI-Research/project2_multi_agent/prompts/agent1a_parsing_gap_detection.md:7)、[执行实现](E:/AI-Research/project2_multi_agent/core/agent1a_parsing_gap_detection.py:188)。

## 2. 缺口驱动澄清问题生成 Agent

**解决的问题**：澄清问题重复、过多、遗漏关键动作，或者引入未确认设计方案。

**输入**：`requirement_text`、`main_flow`、`action_gap_candidates`。

**核心处理逻辑**：只读取 `has_gap=true` 的候选；按缺口类型生成抽象问题；进行语义去重；优先保证不同动作覆盖；控制问题数量。

**输出**：`open_questions`。

**边界**：不能重新判断或新增缺口类型；不能脱离候选集合自由提问；不能引入 UI、机制或实现细节。

**适用场景**：需求澄清清单、评审会议准备、人工补充信息入口。

**不适用场景**：需要提供候选解决方案、交互设计或业务建议的场景。

**项目证据**：[生成与压缩规则](E:/AI-Research/project2_multi_agent/prompts/agent1b_question_generation.md:23)、[执行实现](E:/AI-Research/project2_multi_agent/core/agent1b_question_generation.py:138)。

## 3. 证据约束风险审查 Agent

**解决的问题**：风险分析泛化为任何系统都适用的 checklist。

**输入**：`requirement_text`、需求解析结果、澄清问题结果。

**核心处理逻辑**：优先从 `open_questions` 获取风险证据；对需求中已出现但边界不明的内容做抽象风险判断；将每项问题放入最直接的风险类别。

**输出**：`ambiguity_risks`、`missing_info`、`edge_case_risks`、`permission_risks`、`data_risks`、`performance_risks`。

**边界**：不能引入新业务机制、具体异常原因、解决方案或指标；无证据的风险类别应为空。

**适用场景**：需求风险评审、测试关注范围识别、信息缺失分析。

**不适用场景**：完整安全审计、威胁建模、行业合规或架构风险分析。

**项目证据**：[风险来源与分类规则](E:/AI-Research/project2_multi_agent/prompts/agent_2_risk_review.md:21)、[执行实现](E:/AI-Research/project2_multi_agent/core/agent2_risk_analysis.py:51)。

## 4. 受控测试草案设计 Agent

**解决的问题**：信息不足时仍生成详细步骤和伪完整测试用例。

**输入**：`requirement_text`、需求解析结果、风险分析结果。

**核心处理逻辑**：从已知动作提取核心测试点；将已有风险转化为抽象测试方向；只提取明确的最小验收结果；信息不足时停止具体用例生成。

**输出**：`core_test_points`、`edge_test_points`、`performance_test_points`、`acceptance_criteria`、`test_case_drafts`。

**边界**：不能补充规则、输入值、错误文案、技术实现或具体性能指标；输出定位是草案而非完整用例。

**适用场景**：需求早期测试设计、需求信息不足的测试分析。

**不适用场景**：完整手工用例编写、自动化脚本生成、测试数据生成。

**项目证据**：[停止生成规则](E:/AI-Research/project2_multi_agent/prompts/agent_3_test_design.md:6)、[执行实现](E:/AI-Research/project2_multi_agent/core/agent3_test_design.py:50)。

## 5. 可追溯结果汇总与复核路由 Agent

**解决的问题**：汇总阶段重新扩写问题和风险，以及未经确认的结果直接进入下游。

**输入**：原始需求、需求解析、澄清问题、风险分析和测试草案。

**核心处理逻辑**：只汇总上游已有信息；原样复用关键问题；根据缺口、风险和草案状态判断是否需要人工复核。

**输出**：`requirement_summary`、`risk_summary`、`test_recommendation`、`human_review_required`、`critical_open_questions`。

**边界**：不能新增、改写、拆分或具体化问题；不能新增风险、测试方向和业务假设；不负责最终决策。

**适用场景**：测试负责人复核、需求评审摘要、AI 输出治理和审批入口。

**不适用场景**：需要汇总阶段继续分析、自动决策或自动批准的场景。

**项目证据**：[汇总与复核规则](E:/AI-Research/project2_multi_agent/prompts/agent_4_summary.md:6)、[执行实现](E:/AI-Research/project2_multi_agent/core/agent4_result_summary.py:51)。

## 6. 澄清问题收敛 Agent

**状态**：兼容实验能力，默认关闭。

**解决的问题**：已有澄清问题重复、语义重叠或数量过多。

**输入**：`requirement_text`、包含 `open_questions` 和 `main_flow` 的解析结果。

**核心处理逻辑**：删除重复问题；合并语义重叠问题；优先保留流程问题和独立动作问题；将数量控制在约 1～3 个。

**输出**：收敛后的 `open_questions`。

**边界**：只能筛选已有问题，不能新增问题类型、具体实现或设计内容。

**适用场景**：已有问题集的压缩、兼容方案对比实验。

**不适用场景**：从动作缺口直接生成问题，或输入中没有现成 `open_questions` 的场景。

**项目证据**：[收敛规则](E:/AI-Research/project2_multi_agent/prompts/extensions/agent1_two_stage/prompts/agent1_question_decision.md:3)、[扩展实现](E:/AI-Research/project2_multi_agent/extensions/agent1_two_stage/agent1_question_decision.py:63)、[条件调用](E:/AI-Research/project2_multi_agent/core/pipeline_runner.py:53)。

当前主链路传给该扩展的是不包含 `open_questions` 的新解析结果，因此存在输入契约不匹配。它是真实存在的实验 Agent，但不能视为当前稳定主链路能力。

未单独提取旧版四 Agent 实现，因为其职责与上述能力重复。也未提取双通道风险 Agent，因为对应 Prompt 文件缺失且当前未接入 Pipeline。