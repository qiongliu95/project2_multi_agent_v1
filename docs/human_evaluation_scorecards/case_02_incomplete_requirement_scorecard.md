# Human Evaluation Scorecard - case_02_incomplete_requirement

## Evaluation Scope

本 scorecard 用于人工评估最终 3 个 evaluation case 中的 `case_02_incomplete_requirement`。

注意：本次对应真实运行是 `text + real`，`context_sources=[]`，因此本 scorecard 评估的是无 Context 路径下的信息不足处理能力。Context 对比请另参考 Context Comparison 产物。

## Requirement / Context

| 项目 | 内容 |
|---|---|
| Case | `case_02_incomplete_requirement` |
| 类型 | 信息明显不足需求 |
| 需求文件 | `data/evaluation_cases/case_02_incomplete_requirement/requirement.md` |
| 评估目标文件 | `data/evaluation_cases/case_02_incomplete_requirement/expected_focus.md` |
| Context | 无 Context，`context_sources=[]` |
| 运行模式 | `mode=text`, `agent_mode=real` |

需求摘要：

- 为账号系统增加手机号登录能力。
- 用户可在登录页选择手机号登录，输入手机号后进入验证流程，验证通过后登录系统。
- 系统需要记录手机号登录相关操作日志。
- 当前需求明确列出多个未明确信息。

## Run Evidence

| 证据 | 路径 |
|---|---|
| run_id | `verify_text_real_20260808_090039_228710` |
| final result | `outputs/evaluation_runs/case_02_incomplete_requirement/final_result.json` |
| Agent1A output | `outputs/evaluation_runs/case_02_incomplete_requirement/agent1a_output.json` |
| Agent1B output | `outputs/evaluation_runs/case_02_incomplete_requirement/agent1b_output.json` |
| Agent2 output | `outputs/evaluation_runs/case_02_incomplete_requirement/agent2_output.json` |
| Agent3 output | `outputs/evaluation_runs/case_02_incomplete_requirement/agent3_output.json` |
| Agent4 output | `outputs/evaluation_runs/case_02_incomplete_requirement/agent4_output.json` |
| workflow events | `outputs/evaluation_runs/case_02_incomplete_requirement/workflow_trace/workflow_events.jsonl` |
| agent traces | `outputs/evaluation_runs/case_02_incomplete_requirement/workflow_trace/agent_traces.jsonl` |
| run log | `outputs/evaluation_runs/case_02_incomplete_requirement/run.log` |

Workflow evidence:

- `workflow_state.control.status`: `completed`
- `workflow_state.control.stop_reason`: `null`
- `workflow_state.control.human_review_required`: `true`

## Agent Key Output Summary

| Agent | 关键输出摘要 | 原始输出 |
|---|---|---|
| Agent1A | `main_flow=5`; `action_gap_candidates=5`; `specific_unknowns=8`; `unassigned_unknowns=0`; `context_refs=[]` | `agent1a_output.json` |
| Agent1B | `open_questions=8`; `question_sources=8` | `agent1b_output.json` |
| Agent2 | `risk_items=14`; old risk arrays: `ambiguity_risks=8`, `missing_info=8`, `edge_case_risks=3`, `permission_risks=0`, `data_risks=2`, `performance_risks=1` | `agent2_output.json` |
| Agent3 | `core_test_points=5`; `edge_test_points=5`; `performance_test_points=1`; `acceptance_criteria=5`; `test_case_drafts=1` | `agent3_output.json` |
| Agent4 | 输出 `requirement_summary`, `risk_summary`, `test_recommendation`, `human_review_required`, `critical_open_questions=8` | `agent4_output.json` |

## must_cover

人工评估时重点确认：

- Agent1A 是否输出具体 `specific_unknowns`，而不是只写“手机号登录规则未定义”。
- Agent1A 是否覆盖验证方式、凭证有效期、失败处理、发送频率、未注册手机号、多账号绑定同一手机号、登录失败日志、日志字段。
- Agent1B 是否基于 Agent1A artifact 生成具体、可回答的问题。
- Agent2 是否将缺失信息映射为风险。
- Agent3 是否把 unknown 相关内容表达为验证关注方向或待确认项，而不是确定性测试结论。

## valid_optional

以下内容出现时可视为合理但非必需：

- 针对手机号格式、手机号归属或异常输入提出边界关注点。
- 针对日志记录失败、重复提交、验证流程中断提出风险。
- 针对多账号和手机号关系提出数据一致性风险。

## unsupported

以下内容若出现，应由人工标记为问题：

- 编造手机号登录一定使用短信验证码。
- 编造验证码有效期、失败次数、锁定时间或发送频率。
- 编造日志字段。
- Agent1B 提出“手机号登录的具体规则是什么”这类宽泛问题，而不是围绕明确 unknown 提问。
- Agent3 把未确定规则写成确定验收标准。

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
