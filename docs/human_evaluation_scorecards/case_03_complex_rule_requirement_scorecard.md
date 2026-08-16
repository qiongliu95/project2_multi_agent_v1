# Human Evaluation Scorecard - case_03_complex_rule_requirement

## Evaluation Scope

本 scorecard 用于人工评估最终 3 个 evaluation case 中的 `case_03_complex_rule_requirement`。

注意：本次对应真实运行是 `text + real`，`context_sources=[]`，因此本 scorecard 评估的是规则已经写入 requirement_text 时的 Workflow 表现。Context View 对复杂规则传递的增益请另参考 Context Comparison 产物。

## Requirement / Context

| 项目 | 内容 |
|---|---|
| Case | `case_03_complex_rule_requirement` |
| 类型 | 规则复杂需求 |
| 需求文件 | `data/evaluation_cases/case_03_complex_rule_requirement/requirement.md` |
| 评估目标文件 | `data/evaluation_cases/case_03_complex_rule_requirement/expected_focus.md` |
| Context | 无 Context，`context_sources=[]` |
| 运行模式 | `mode=text`, `agent_mode=real` |

需求摘要：

- 为订单系统增加优惠券自动选择能力。
- 系统在提交订单前自动选择最优优惠券，并允许用户手动切换为其他可用优惠券。
- 需求包含可用性规则、最优选择规则、手动切换规则、金额计算规则和日志规则。
- 需求明确列出三条未确定内容。

## Run Evidence

| 证据 | 路径 |
|---|---|
| run_id | `verify_text_real_20260808_090112_202115` |
| final result | `outputs/evaluation_runs/case_03_complex_rule_requirement/final_result.json` |
| Agent1A output | `outputs/evaluation_runs/case_03_complex_rule_requirement/agent1a_output.json` |
| Agent1B output | `outputs/evaluation_runs/case_03_complex_rule_requirement/agent1b_output.json` |
| Agent2 output | `outputs/evaluation_runs/case_03_complex_rule_requirement/agent2_output.json` |
| Agent3 output | `outputs/evaluation_runs/case_03_complex_rule_requirement/agent3_output.json` |
| Agent4 output | `outputs/evaluation_runs/case_03_complex_rule_requirement/agent4_output.json` |
| workflow events | `outputs/evaluation_runs/case_03_complex_rule_requirement/workflow_trace/workflow_events.jsonl` |
| agent traces | `outputs/evaluation_runs/case_03_complex_rule_requirement/workflow_trace/agent_traces.jsonl` |
| run log | `outputs/evaluation_runs/case_03_complex_rule_requirement/run.log` |

Workflow evidence:

- `workflow_state.control.status`: `completed`
- `workflow_state.control.stop_reason`: `null`
- `workflow_state.control.human_review_required`: `true`

## Agent Key Output Summary

| Agent | 关键输出摘要 | 原始输出 |
|---|---|---|
| Agent1A | `main_flow=3`; `action_gap_candidates=3`; `specific_unknowns=3`; `unassigned_unknowns=0`; `context_refs=[]` | `agent1a_output.json` |
| Agent1B | `open_questions=3`; `question_sources=3` | `agent1b_output.json` |
| Agent2 | `risk_items=8`; old risk arrays: `ambiguity_risks=2`, `missing_info=3`, `edge_case_risks=3`, `permission_risks=0`, `data_risks=2`, `performance_risks=0` | `agent2_output.json` |
| Agent3 | `core_test_points=3`; `edge_test_points=8`; `performance_test_points=0`; `acceptance_criteria=3`; `test_case_drafts=1` | `agent3_output.json` |
| Agent4 | 输出 `requirement_summary`, `risk_summary`, `test_recommendation`, `human_review_required`, `critical_open_questions=3` | `agent4_output.json` |

## must_cover

人工评估时重点确认：

- Agent1A 是否识别自动选择、手动切换、金额重算、日志记录等主流程。
- Agent1A 是否把优惠券可用性规则、最优选择规则、手动切换规则和金额计算规则写入 known_conditions。
- Agent1A 是否把三条“未确定”内容作为 `specific_unknowns`，而不是当作已确认规则。
- Agent1B 是否围绕叠加使用、金额变化后选择保留、不可用原因展示优先级生成具体澄清问题。
- Agent2 是否识别规则冲突、金额计算、可用性边界、手动选择覆盖、日志记录等风险。
- Agent3 是否基于业务规则生成验证关注点。

## valid_optional

以下内容出现时可视为合理但非必需：

- 针对优惠金额相同、过期时间相同、创建时间相同提出边界验证。
- 针对订单商品、门店、金额变化后的重新计算提出额外风险。
- 针对日志字段完整性提出验证关注点。

## unsupported

以下内容若出现，应由人工标记为问题：

- 编造优惠券叠加规则。
- 编造不可用原因展示优先级。
- 将运费参与优惠券抵扣。
- 忽略“用户手动切换后不得再次自动覆盖”的规则。
- 将 unknown 直接写成确定性验收标准。

## Human Scoring

请人工填写评分。不要由脚本或模型自动评分。

| 维度 | 评分 0/1/2 | Evidence notes | Reviewer notes |
|---|---:|---|---|
| Grounding |  |  |  |
| Boundary |  |  |  |
| Completeness |  |  |  |
| Uncertainty Handling |  |  |  |
| Relevance |  |  |  |
| Usefulness |  |  |  |

## Overall

请人工选择：

- [ ] Pass
- [ ] Partial
- [ ] Fail

Blocking:

- [ ] Yes
- [ ] No

说明：Overall 不通过六项简单平均分或总分机械计算。Blocking 不等于低分；只有当问题导致核心业务事实、关键流程或主要输出不可依赖、无法继续使用时，才选择 Yes。

Reviewer notes:

```text

```
