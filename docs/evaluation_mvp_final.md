# Evaluation MVP 最终收敛方案

> 当前状态：本方案已经执行并由 `docs/project_exit_report.md` 完成最终收口。
>
> 本文保留为 Evaluation MVP 的方法论和停止标准说明；项目当前最终结论以 `docs/project_exit_report.md` 中的 `exit_approved` 为准。文中“仍缺的必要评估工作”和“做到哪里停止”描述的是当时进入 Project Exit 前的执行清单，不代表当前仍未完成。

## 1. 目标

本项目的 Evaluation 不是为了建设完整评估平台，而是为了给 Multi-Agent 需求分析作品集提供明确停止标准，避免继续根据单次模型输出反复修改 Prompt、Context 或代码。

最终 Evaluation 只回答三个问题：

1. 当前 Workflow 是否具备可运行、可观察、可复核的系统条件。
2. 三个核心 case 是否能够证明需求理解、unknown 保留、风险识别和受控验证关注点生成基本成立。
3. Text Only、Structured Context、Human Context Compiler 三种路径是否各自证明了它们应该证明的事情。

Context 能力本身不是目标。它只在能够降低人工需求分析成本、提高风险识别质量、提升历史经验复用效率时才有评估价值。

## 2. 当前 Evaluation 应如何组织

### 2.1 Minimal System Readiness

System Readiness 是 run-level 的确定性检查，只判断一次运行是否具备被评估的技术条件，不判断模型语义质量。

必须检查：

| 检查项 | 证据来源 | 阻塞条件 |
|---|---|---|
| Workflow 是否正常完成或按 contract 合法停止 | `result.json`、`workflow_events.jsonl` | 非预期异常、无法区分 API/网络错误与模型输出问题 |
| Agent 顺序是否正确 | `agent_traces.jsonl`、`workflow_events.jsonl` | 顺序不是 Agent1A -> Agent1B -> Agent2 -> Agent3 -> Agent4 |
| Stage Artifact 是否生成并传递 | `result.json`、stage output files | 下游必需 artifact 缺失 |
| Trace 是否可复核 | `workflow_events.jsonl`、`agent_traces.jsonl`、`tool_traces.jsonl` | 缺少核心事件或无法对应 run_id |
| Context 是否进入预期 Stage | trace 中的 `context_view`、`context_consumption` | Structured/Compiler 路径无 Context View 或 item id 不可追踪 |
| 明确 contract violation 是否存在 | normalized output、trace warning | 例如必填字段缺失、无效 `context_refs`、无法解析 JSON |

System Readiness 只输出 `pass` 或 `fail`。失败会阻塞本次 Evaluation Run。它不判断风险是否有价值、问题是否足够精准、测试关注点是否专业。

### 2.2 Final Human Evaluation

人工评估用于判断开放推理质量。它不要求唯一 Golden Answer，而使用：

- `must_cover`：必须覆盖的关键点。
- `valid_optional`：合理但非必需的补充点。
- `unsupported`：不应出现的无依据结论或越界内容。

人工评分维度：

| 维度 | 评分 |
|---|---|
| Grounding | 0/1/2 |
| Boundary | 0/1/2 |
| Completeness | 0/1/2 |
| Uncertainty Handling | 0/1/2 |
| Relevance | 0/1/2 |
| Usefulness | 0/1/2 |

Overall 只允许人工填写：`Pass`、`Partial`、`Fail`。

统一评分锚点：

- `2`：核心要求基本满足，仅有轻微问题，不影响主要结果。
- `1`：存在明确实质问题，但核心能力仍存在，结果仍可部分使用。
- `0`：核心能力缺失，或问题已导致主要输出不可信/不可用。

同一个问题可以同时成为多个 Criteria 的证据，但必须分别说明它对该维度造成的具体影响，不能因为同一个问题机械地在多个维度重复扣分。

人工评估还需要单独判断 `Blocking`: `Yes` / `No`。`Overall` 不通过六项简单平均分或总分机械计算，`Blocking` 也不等于低分。Blocking 重点判断问题是否已经导致核心业务事实、关键流程或主要输出不可依赖、无法继续使用。

### 2.3 Context Path Evidence

三种路径不需要做完整 case x path 矩阵。它们验证的问题不同：

| 路径 | 验证目标 | 是否作为核心质量评估 |
|---|---|---|
| Text Only | 基础五 Agent Workflow 是否成立 | 是，作为核心 baseline |
| Structured Context | Context View 是否能进入 Agent 并影响分析空间 | 是，但结论必须人工判断 |
| Human Context Compiler | 人工业务格式是否能编译为 Runtime Context 并进入现有 Structured 链路 | 否，仅验证路径可用性和输入方式合理性 |

`summary_metrics` 中的 unknown 数量、context_refs 数量、风险数量只能作为人工评估证据，不能自动推出“Context 改善了结果”。

Human Context Compiler “降低手写 JSON 成本”是设计目标，不是本次运行结果已经验证的产品结论。

## 3. 三种运行路径的关系

### Text Only

Text Only 是基础能力评估路径。它回答：

- 没有外部 Context 时，Workflow 是否能完整执行。
- Agent1A 是否能从当前需求中提取主流程和缺口。
- Agent1B 是否能基于 Agent1A Artifact 生成澄清问题。
- Agent2 是否能识别主要风险。
- Agent3 是否能在信息不足时避免伪完整测试结论。
- Agent4 是否能汇总 Stage Artifact，而不是重新分析。

### Structured Context

Structured Context 是 Runtime Context 输入路径。它回答：

- Context Package V2 是否能转换为 Agent Context View。
- Context item id、source_ref、context_refs 是否可追踪。
- 已知规则、限制、流程、unknown 是否能影响 Agent1A/Agent2/Agent3 的分析空间。
- Context 是否减少宽泛 unknown，或让风险和验证关注点更贴近业务。

这些变化必须由人工结合输出质量判断，不能只根据数量变化自动判定。

### Human Context Compiler

Human Context Compiler 是上下文准备路径。它回答：

- 业务人员不直接手写 Runtime JSON 的路线是否跑通。
- Compiler 输出是否能够复用现有 Structured Context Runtime。
- 编译后 Context 是否保留基本规则、限制、unknown 和来源。

它不在本次 Evaluation 中证明长期维护成本已经降低。这个结论需要真实使用者维护样本和耗时数据。

## 4. 已有材料的处理方式

| 材料 | 当前状态 | 最终使用方式 |
|---|---|---|
| `docs/evaluation_framework.md` | 设计参考 | 历史参考，以本文为最终 MVP 口径 |
| `docs/evaluation_readiness_gate.md` | 设计参考 | 历史参考 |
| `docs/evaluation_failure_taxonomy.md` | 设计参考 | 历史参考 |
| `docs/evaluation_rubric.md` | 评分参考 | 可继续复用评分维度 |
| `docs/workflow_evaluation_report.md` | 既有运行分析 | 作为证据快照，不作为最终结项结论 |
| `docs/context_value_evaluation.md` | Context 对比分析 | 作为证据快照，不自动推出改善结论 |
| `docs/context_comparison_baseline.md` | 对比方法说明 | 历史参考 |
| `docs/human_evaluation_scorecards/*.md` | 人工评估工作表 | 保留，作为最终人工评分输入 |
| `outputs/evaluation_runs/` | Text Only 核心运行结果 | 作为三大核心 case 的主要证据 |
| `outputs/context_comparison_p1_real/` | Context path 对比结果 | 作为辅助证据，失败 run 不扩大为新开发任务 |

## 5. 最终 Exit Criteria

项目满足以下条件即可结项：

1. Minimal System Readiness 对选定证据 run 无 blocking failure。
2. 三个核心 case 均可完成有效人工评估。
3. 三个核心产品假设经人工评估后成立或基本成立：
   - 信息不足时，unknown 能被保留，而不是伪造成确定事实。
   - Context 能实际影响或缩小后续分析空间。
   - 风险和 unknown 能约束 Agent3，避免伪完整生成。
4. 剩余问题主要属于：
   - 输出颗粒度差异。
   - 风险数量波动。
   - 表达质量差异。
   - 偶发模型波动。
   - 当前轻量架构能力边界。
5. 已知限制已记录，并且不存在阻塞核心演示的确定性系统错误。

## 6. 目前仍缺的必要评估工作

真正必要的工作只有三项：

1. 人工填写三个核心 case 的 scorecard。
2. 人工检查一个代表性 Context path 对比证据，确认 Structured Context 是否确实改变了分析空间。
3. 将人工评分和结论回填到 `docs/project_exit_report.md`。

不需要继续新增 case、扩展自动指标、做多模型 Benchmark、引入 LLM Judge 或继续根据单次失败修改 Prompt。

## 7. 做到哪里停止

当以下内容完成后停止：

1. 三个核心 scorecard 有人工评分和 notes。
2. Context path 证据完成一次人工补充判断。
3. `docs/project_exit_report.md` 更新为最终结项结论。
4. 已知限制列表保留。

停止后，后续问题不再作为本阶段继续开发理由，只进入下一阶段候选 backlog。
