# Human Evaluation Scorecard - case_01_complete_requirement

## Evaluation Scope

本 scorecard 用于人工评估最终 3 个 evaluation case 中的 `case_01_complete_requirement`。

注意：本次对应真实运行是 `text + real`，`context_sources=[]`，因此本 scorecard 评估的是无 Context 路径下的 Workflow 表现。Context 对比请另参考 Context Comparison 产物。

## Requirement / Context

| 项目 | 内容 |
|---|---|
| Case | `case_01_complete_requirement` |
| 类型 | 信息相对完整需求 |
| 需求文件 | `data/evaluation_cases/case_01_complete_requirement/requirement.md` |
| 评估目标文件 | `data/evaluation_cases/case_01_complete_requirement/expected_focus.md` |
| Context | 无 Context，`context_sources=[]` |
| 运行模式 | `mode=text`, `agent_mode=real` |

需求摘要：

- 为账号系统增加邮箱绑定能力。
- 用户登录后可在个人资料页绑定邮箱。
- 绑定邮箱需要邮箱验证码校验。
- 已定义验证码有效期、发送频率、邮箱唯一性、账号唯一绑定、邮箱格式、换绑规则、日志字段和异常处理。

## Run Evidence

| 证据 | 路径 |
|---|---|
| run_id | `verify_text_real_20260808_085957_891490` |
| final result | `outputs/evaluation_runs/case_01_complete_requirement/final_result.json` |
| Agent1A output | `outputs/evaluation_runs/case_01_complete_requirement/agent1a_output.json` |
| Agent1B output | `outputs/evaluation_runs/case_01_complete_requirement/agent1b_output.json` |
| Agent2 output | `outputs/evaluation_runs/case_01_complete_requirement/agent2_output.json` |
| Agent3 output | `outputs/evaluation_runs/case_01_complete_requirement/agent3_output.json` |
| Agent4 output | `outputs/evaluation_runs/case_01_complete_requirement/agent4_output.json` |
| workflow events | `outputs/evaluation_runs/case_01_complete_requirement/workflow_trace/workflow_events.jsonl` |
| agent traces | `outputs/evaluation_runs/case_01_complete_requirement/workflow_trace/agent_traces.jsonl` |
| run log | `outputs/evaluation_runs/case_01_complete_requirement/run.log` |

Workflow evidence:

- `workflow_state.control.status`: `completed`
- `workflow_state.control.stop_reason`: `null`
- `workflow_state.control.human_review_required`: `true`

## Agent Key Output Summary

| Agent | 关键输出摘要 | 原始输出 |
|---|---|---|
| Agent1A | `main_flow=5`; `action_gap_candidates=5`; `specific_unknowns=5`; `unassigned_unknowns=0`; `context_refs=[]` | `agent1a_output.json` |
| Agent1B | `open_questions=5`; `question_sources=5` | `agent1b_output.json` |
| Agent2 | `risk_items=19`; old risk arrays: `ambiguity_risks=4`, `missing_info=5`, `edge_case_risks=4`, `permission_risks=2`, `data_risks=3`, `performance_risks=2` | `agent2_output.json` |
| Agent3 | `core_test_points=10`; `edge_test_points=21`; `performance_test_points=2`; `acceptance_criteria=7`; `test_case_drafts=1` | `agent3_output.json` |
| Agent4 | 输出 `requirement_summary`, `risk_summary`, `test_recommendation`, `human_review_required`, `critical_open_questions=5` | `agent4_output.json` |

## must_cover

人工评估时重点确认：

- Agent1A 是否识别邮箱绑定与换绑的主流程。
- Agent1A 是否保留已明确规则，包括验证码有效期、发送频率、邮箱唯一、账号唯一绑定、邮箱格式和日志字段。
- Agent1A 是否避免把已明确规则再次识别成缺口。
- Agent1B 是否避免提出“邮箱绑定规则是什么”这类宽泛问题。
- Agent2 风险是否主要基于 requirement 中已有信息和 Agent1A/Agent1B artifact。
- Agent3 是否基于已给规则生成验证关注点。

## valid_optional

以下内容出现时可视为合理但非必需：

- 针对验证码错误、过期、邮箱占用、未登录等异常场景补充验证关注点。
- 针对日志记录完整性提出合理风险。
- 针对换绑流程顺序提出人工确认问题。

## unsupported

以下内容若出现，应由人工标记为问题：

- 编造需求中没有出现的验证码长度、重试次数、锁定时间。
- 编造邮箱服务商限制、实名认证、密码策略或其他无关机制。
- 把已明确的验证码有效期、发送频率、邮箱唯一性再次当作 unknown。
- 输出与邮箱绑定无关的登录方式、账号安全或权限风险。

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
