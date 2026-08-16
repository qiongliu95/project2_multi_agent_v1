# Human Evaluation Scorecard - Context Path Supplement

> 文档状态：人工评估工作表。本文用于补充判断 Context path 证据；其中数量指标只能作为人工评估线索，不能自动推出 Context 改善结论。

## Evaluation Scope

本 scorecard 用于补充评估当前项目的三种输入路径：

- `A_text_only`
- `B_structured_context`
- `C_compiler_context`

本补充评估只选择 `case_01_complete_requirement`，因为该 case 的三条路径均已有真实完成运行结果，适合用于验证 Context 路径是否能够进入 Workflow、影响 Stage Artifact，并被 Trace 复核。

本 scorecard 不替代三个核心 Text-only case 的人工评估。它只补足 Structured Context 和 Human Context Compiler 路径的证据边界。

## Evidence Boundary

请严格按以下边界解读本 scorecard：

- `summary_metrics.json` 中的 unknown 数量、`context_refs` 数量、`risk_items` 数量、Agent3 output count 等，只作为人工评估证据线索。
- 数量变化只能说明输出结构发生了变化，不能自动说明 Context 改善了分析质量。
- Context 是否改善 Workflow 效果，必须由人工结合 `must_cover`、`valid_optional`、`unsupported` 和具体 Agent 输出内容判断。
- Human Context Compiler “降低手写 JSON 成本”属于设计目标，不作为本次运行评估已验证结论。
- 本次运行可以证明 Compiler 输出能够进入 Structured Context Runtime 并被 Workflow 消费，但不能证明它实际降低了人工维护成本。
- 本 scorecard 不评估 Formal Reliability、多模型稳定性、LLM Judge 或自动语义质量。

## Requirement / Context

| 项目 | 内容 |
|---|---|
| Case | `case_01_complete_requirement` |
| 类型 | 信息相对完整需求 |
| 需求文件 | `data/evaluation_cases/case_01_complete_requirement/requirement.md` |
| 评估目标文件 | `data/evaluation_cases/case_01_complete_requirement/expected_focus.md` |
| Structured Context | `data/context/evaluation/case_01_structured_context_v2.json` |
| Human Context | `data/human_context/evaluation/case_01_email_binding.md` |
| Comparison output root | `outputs/context_comparison_p1_real` |

需求摘要：

- 为账号系统增加邮箱绑定能力。
- 用户登录后可在个人资料页绑定邮箱。
- 绑定邮箱需要邮箱验证码校验。
- 需求已定义验证码有效期、发送频率、邮箱唯一性、账号唯一绑定、邮箱格式、换绑规则、日志字段和异常处理。

## Run Evidence

| Version | run_id | status | result | trace | archived output |
|---|---|---|---|---|---|
| `A_text_only` | `verify_text_real_20260808_095343_916796` | `completed` | `outputs/verify_runs/verify_text_real_20260808_095343_916796/result.json` | `outputs/traces/verify_text_real_20260808_095343_916796` | `outputs/context_comparison_p1_real/case_01_complete_requirement/A_text_only` |
| `B_structured_context` | `verify_structured_real_20260808_095423_807687` | `completed` | `outputs/verify_runs/verify_structured_real_20260808_095423_807687/result.json` | `outputs/traces/verify_structured_real_20260808_095423_807687` | `outputs/context_comparison_p1_real/case_01_complete_requirement/B_structured_context` |
| `C_compiler_context` | `verify_structured_real_20260808_095500_829572` | `completed` | `outputs/verify_runs/verify_structured_real_20260808_095500_829572/result.json` | `outputs/traces/verify_structured_real_20260808_095500_829572` | `outputs/context_comparison_p1_real/case_01_complete_requirement/C_compiler_context` |

Supporting summary:

- `outputs/context_comparison_p1_real/summary_metrics.json`
- `outputs/context_comparison_p1_real/summary.md`

## Structural Evidence for Human Review

以下指标只作为人工评估证据，不构成自动质量结论。

| Version | Context item counts | Agent1A specific unknowns | Agent1A context refs | Agent1B questions | risk_items | risk context_refs | Agent3 output count |
|---|---|---:|---:|---:|---:|---:|---:|
| `A_text_only` | `{}` | 7 | 0 | 7 | 21 | 0 | 43 |
| `B_structured_context` | `confirmed_facts=2`, `business_rules=8`, `constraints=2`, `process_flows=2`, `unknowns=0` | 4 | 9 | 4 | 4 | 4 | 28 |
| `C_compiler_context` | `confirmed_facts=8`, `business_rules=10`, `constraints=2`, `process_flows=5`, `unknowns=2` | 2 | 2 | 2 | 12 | 2 | 26 |

## Trace Context Consumption Evidence

以下内容用于确认 Context 是否进入预期 Stage，不用于自动判断语义改善。

| Version | Agent1A consumed Context | Agent1B consumed Context | Agent2 consumed Context | Agent3 consumed Context | Agent4 consumed Context |
|---|---|---|---|---|---|
| `A_text_only` | none | none | none | none | none |
| `B_structured_context` | `confirmed_facts=2`, `business_rules=8`, `constraints=2`, `process_flows=2` | none | `confirmed_facts=2`, `business_rules=8`, `constraints=2`, `process_flows=2` | `confirmed_facts=2`, `business_rules=8`, `constraints=2`, `process_flows=2` | `confirmed_facts=2`, `business_rules=8`, `constraints=2`, `process_flows=2`, `source_refs=1` |
| `C_compiler_context` | `confirmed_facts=8`, `business_rules=10`, `constraints=2`, `process_flows=5`, `unknowns=2` | none | `confirmed_facts=8`, `business_rules=10`, `constraints=2`, `process_flows=5`, `unknowns=2` | `confirmed_facts=8`, `business_rules=10`, `constraints=2`, `process_flows=5`, `unknowns=2` | `confirmed_facts=8`, `business_rules=10`, `constraints=2`, `process_flows=5`, `unknowns=2`, `source_refs=27` |

## Agent Output Evidence to Review

请人工打开以下文件进行具体内容判断。

| Version | Agent1A | Agent1B | Agent2 | Agent3 | Agent4 |
|---|---|---|---|---|---|
| `A_text_only` | `outputs/context_comparison_p1_real/case_01_complete_requirement/A_text_only/agent1a_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/A_text_only/agent1b_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/A_text_only/agent2_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/A_text_only/agent3_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/A_text_only/agent4_output.json` |
| `B_structured_context` | `outputs/context_comparison_p1_real/case_01_complete_requirement/B_structured_context/agent1a_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/B_structured_context/agent1b_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/B_structured_context/agent2_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/B_structured_context/agent3_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/B_structured_context/agent4_output.json` |
| `C_compiler_context` | `outputs/context_comparison_p1_real/case_01_complete_requirement/C_compiler_context/agent1a_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/C_compiler_context/agent1b_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/C_compiler_context/agent2_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/C_compiler_context/agent3_output.json` | `outputs/context_comparison_p1_real/case_01_complete_requirement/C_compiler_context/agent4_output.json` |

## must_cover

人工评估时重点确认：

- Structured Context 是否进入 Agent1A、Agent2、Agent3、Agent4 的 Context View。
- Human Context Compiler 输出是否进入 Structured Context Runtime，并被 Agent Context View 消费。
- Context item ID 是否能通过 Trace 追踪到具体 Agent 消费记录。
- Context 是否帮助 Agent1A 区分已知规则和真正 unknown。
- Agent1B 是否继续基于 Agent1A Stage Artifact 生成问题，而不是直接重新消费 Context。
- Agent2 的 `risk_items` 是否能关联已有规则、限制、unknown 或 context_refs。
- Agent3 是否基于风险和规则生成验证关注点，而不是生成伪完整结论。

## valid_optional

以下内容出现时可视为合理但非必需：

- Structured Context 和 Compiler Context 对 unknown 数量产生不同影响。
- Compiler Context 因包含更多 item 而让 Agent 消费更多 source refs。
- Context 路径下 Agent3 输出数量减少，但具体内容更聚焦。
- Context 路径下 risk_items 数量变化，但风险来源更可追踪。

## unsupported

以下内容若出现，应由人工标记为问题：

- 仅凭 unknown 数量下降就断言 Context 改善了分析质量。
- 仅凭 `context_refs` 数量增加就断言风险或测试关注点更可靠。
- 将 Compiler 路径的可运行性解释为“已验证降低人工维护成本”。
- Context 引入了 requirement 或 context 中没有依据的新业务事实。
- Agent3 将 unknown 直接写成确定性验收标准。
- Agent4 基于原始 Context 重新生成新的风险或测试结论。

## Human Scoring

请人工填写评分。不要由脚本或模型自动评分。

| 维度 | 评分 0/1/2 | Evidence notes | Reviewer notes |
|---|---:|---|---|
| Context Grounding |  |  |  |
| Context Usefulness |  |  |  |
| Unknown Reduction Quality |  |  |  |
| Traceability |  |  |  |
| Compiler Runtime Compatibility |  |  |  |
| Compiler Equivalence to Structured Context |  |  |  |
| Risk/Test Focus Improvement |  |  |  |
| Boundary Compliance |  |  |  |

## Overall

请人工选择：

- [ ] Pass
- [ ] Partial
- [ ] Fail

Blocking:

- [ ] Yes
- [ ] No

说明：Overall 不通过评分项简单平均分或总分机械计算。Blocking 不等于低分；只有当问题导致 Context 路径证据不可依赖、无法继续用于结项判断时，才选择 Yes。

Reviewer notes:

```text

```

## Project Exit Report Update Guidance

人工评分完成后，再更新 `docs/project_exit_report.md`。

建议只更新以下结论边界：

- Final Human Evaluation 主体基于 3 个 Text-only core case。
- Context 路径通过本 scorecard 的 case_01 三路径补充评估提供证据。
- 本次 MVP 不声称所有 case x 所有路径均完成正式评估。
- 本次 MVP 不声称 Human Context Compiler 已验证降低人工维护成本。
- 本次 MVP 只验证 Compiler 输出可进入 Runtime 链路并被 Workflow 消费。
