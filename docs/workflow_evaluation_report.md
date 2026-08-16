# Multi-Agent Workflow Evaluation

> 文档状态：历史运行分析。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文作为证据快照保留，不单独作为最终结项结论。

## 1. Case Overview

| Case | 类型 | 验证目标 |
|---|---|---|
| case_01_complete_requirement | 信息相对完整需求 | 验证系统不会过度生成 unknown 和风险 |
| case_02_incomplete_requirement | 信息明显不足需求 | 验证 Agent1A 是否识别缺口、Agent1B 是否生成具体澄清问题、Agent2 是否识别风险 |
| case_03_complex_rule_requirement | 规则复杂需求 | 验证复杂规则能否沿 Stage Artifact 传递，并支撑 Agent3 生成基于规则的验证关注点 |

本次三组 case 均使用当前 workflow 的 `text + real agent` 模式运行。

运行产物位于：

- `outputs/evaluation_runs/case_01_complete_requirement/`
- `outputs/evaluation_runs/case_02_incomplete_requirement/`
- `outputs/evaluation_runs/case_03_complex_rule_requirement/`

需要注意：本次运行没有加载 Markdown、Structured Context 或 Auto Context，`workflow_state.context.items` 均为空。因此本报告主要评价 Text 路径下的 Stage Contract 和 Agent 信息隔离效果；不能把本次结果单独作为 Context View 效果验证。

## 2. Agent1A Evaluation

### case_01_complete_requirement

Agent1A 提取了 5 个 main_flow：

- 登录后进入个人资料页绑定邮箱。
- 输入邮箱并完成邮箱验证码校验。
- 系统发送邮箱验证码。
- 更换邮箱时完成短信验证码和新邮箱验证码校验。
- 绑定成功后记录日志。

整体 main_flow 覆盖了需求主路径，但也暴露出一个问题：虽然需求信息相对完整，Agent1A 仍生成了 5 个缺口，包括“个人资料页入口路径”“验证码输入格式”“验证码生成规则或长度”“更换邮箱完整步骤顺序”“日志存储位置或输出格式”。其中部分缺口偏实现细节或页面路径，说明 Agent1A 对“需求分析必要缺口”和“实现细节未定义”的边界仍偏宽。

known_conditions 保留较好，能把验证码有效期、发送频率、邮箱唯一、日志字段等已有规则放入对应动作。specific_unknowns 具体，但数量偏多。

context_refs 均为空，这是预期结果，因为本次未使用 Context Package。

### case_02_incomplete_requirement

Agent1A 提取了 5 个 main_flow：

- 用户选择手机号登录。
- 输入手机号。
- 进入验证流程。
- 验证通过后登录系统。
- 系统记录手机号登录相关操作日志。

缺口识别效果较好。Agent1A 没有把所有动作都泛化成“规则未定义”，而是把具体 unknown 归入相关动作：

- 验证方式未明确。
- 凭证有效期未明确。
- 验证失败处理规则未明确。
- 同一手机号发送频率未明确。
- 未注册手机号是否允许登录未明确。
- 多账号绑定同一手机号如何处理未明确。
- 登录失败是否记录日志未明确。
- 操作日志字段未明确。

这说明 Agent1A -> Agent1B 所需的 `specific_unknowns` 在不完整需求中是有效的。

context_refs 为空，符合 Text 模式预期。

### case_03_complex_rule_requirement

Agent1A 提取了 3 个 main_flow：

- 系统根据当前订单自动选择最优优惠券。
- 用户手动切换为其他可用优惠券。
- 系统记录自动选择、手动切换和重新计算金额的操作日志。

Agent1A 对复杂规则的保留较好。可用性规则、最优选择规则、手动切换规则和日志字段基本进入 known_conditions。三条“未确定”内容被识别为 specific_unknowns：

- 多张优惠券是否允许叠加使用未确定。
- 订单金额变化后是否保留用户手动选择的优惠券未确定。
- 优惠券不可用原因展示优先级未确定。

这组结果证明：即使没有 Context View，只要规则在 requirement_text 中明确出现，Agent1A 的 Stage Artifact 可以把复杂规则和 unknown 结构化传递下去。

context_refs 为空，符合 Text 模式预期。

## 3. Agent1B Evaluation

### 是否基于 Agent1A Artifact 生成问题

三组 case 中，Agent1B 的问题都与 Agent1A 的 `specific_unknowns` 对齐：

- case_01：5 个问题对应 Agent1A 生成的 5 个 unknown。
- case_02：8 个问题对应 Agent1A 生成的 8 个 unknown。
- case_03：3 个问题对应 Agent1A 生成的 3 个 unknown。

这说明 Agent1B 当前已经主要依赖 Agent1A Stage Artifact，而不是自行重新扫描上下文。

### 是否避免重复询问已知信息

case_02 和 case_03 表现较好：

- case_02 没有询问“手机号登录规则是什么”这类宽泛问题，而是聚焦验证方式、有效期、失败处理、发送频率、未注册手机号、日志字段等具体项。
- case_03 没有重复询问已给出的可用性规则、最优券排序规则、金额计算规则，而是聚焦三条未确定内容。

case_01 存在一定过问倾向。问题虽然都来自 Agent1A unknown，但这些 unknown 本身有一部分偏实现细节。因此问题不是 Agent1B 随意发挥，而是 Agent1A 缺口边界偏宽导致下游继承。

### question_sources 是否可追踪

Agent1B 均输出了 `question_sources`，并保留：

- question
- action
- specific_unknown
- context_refs
- unassigned

Text 模式下 `context_refs` 为空是合理的。Stage Artifact 层面的追踪成立，但没有 item 级 Context 追踪。

## 4. Agent2 Evaluation

### 风险分类是否合理

case_02 和 case_03 风险分类基本合理：

- case_02 将验证方式、凭证有效期、失败处理、发送频率、未注册手机号、手机号多账号归属、日志字段等问题转成缺失信息和风险。
- case_03 将叠加使用、订单金额变化后是否保留手动选择、不可用原因展示优先级、金额变化触发重新选择、优惠金额边界、运费不参与抵扣等转成风险。

case_01 风险数量偏多。完整需求仍产生 19 个 risk_items，包含页面入口、验证码格式、验证码长度、日志存储格式等风险。这说明当前 Agent2 会继承 Agent1A 偏宽的 unknown，并进一步放大为风险。

### risk_items 是否覆盖主要风险

三组 case 均生成了 `risk_items`：

- case_01：19 条。
- case_02：14 条。
- case_03：8 条。

risk_items 能覆盖 Agent1B 问题来源，并把部分 known_conditions 转入 related_rules / related_constraints。case_02 和 case_03 中，risk_items 对 Agent3 的后续消费具有明显价值。

### related_unknowns 是否正确

related_unknowns 基本来自 Agent1A/Agent1B 的 unknown：

- case_02 中验证方式、有效期、失败处理、发送频率等都能进入 related_unknowns。
- case_03 中三条未确定内容都能进入 related_unknowns。

case_01 的 related_unknowns 也可追踪，但问题在于 upstream unknown 本身过多，不是 risk_items 构造错误。

### related_rules 是否来自已有 Context

本次没有 Context Package，因此 related_rules 不是来自 Context item，而是来自 Agent1A 的 known_conditions。这个行为符合当前 Text 模式的信息流，但不能验证 Context item 级规则引用能力。

context_refs 均为空，符合本次输入路径。

## 5. Agent3 Evaluation

### 是否消费 risk_items

从输出结果看，Agent3 的 edge_test_points 与 Agent2 risk_items 高度对应：

- case_02 覆盖验证方式、凭证有效期、验证失败处理、发送频率、未注册手机号、多账号手机号、日志记录等风险方向。
- case_03 覆盖优惠券叠加、订单金额变化后手动选择保留、不可用原因展示优先级、订单变化后重新选择、优惠金额边界、运费抵扣边界、日志字段等风险方向。

这说明 Agent3 已经在行为上消费了 Agent2 的风险结构，risk_items 对验证关注点生成有支撑作用。

### 是否把 unknown 错误当确定事实

case_02 和 case_03 中，Agent3 对 unknown 基本使用“关注方向”“信息不足”“待补充”的方式表达，没有把未确定内容写成确定规则。

例如 case_03 中，“多张优惠券是否允许叠加使用未确定”被转化为关注叠加场景的测试方向，而不是直接断言允许或不允许叠加。

### 测试关注点是否来源明确

Stage 来源整体明确：

- core_test_points 主要来自 Agent1A main_flow 和已知业务动作。
- edge_test_points 主要来自 Agent2 risk_items / legacy risk arrays。
- acceptance_criteria 主要来自需求中明确的最小验收结果。

不足是：Text 模式没有 context_refs，因此无法追溯到 Context item，只能追溯到 Stage Artifact。

## 6. Agent4 Evaluation

### 是否以 Stage Artifact 为主汇总

Agent4 输出基本以 Stage Artifact 为主：

- requirement_summary 汇总 Agent1A 的需求结构和已知规则。
- risk_summary 汇总 Agent2 的风险。
- test_recommendation 汇总 Agent3 的测试关注点。
- critical_open_questions 直接复用 Agent1B open_questions。

三组 case 的 `human_review_required` 均为 true，原因是均存在 open_questions、missing_info 或信息不足测试草案。

### 是否重新分析 Context

本次没有 Context，因此 Agent4 不存在重新分析 Context 的问题。

但 case_01 的最终汇总会显得风险较多，这是因为上游 Agent1A/Agent2 已经生成了较多 unknown 和 risk_items，Agent4 只是继承汇总，并未明显新增独立风险。

## 7. Overall Conclusion

### 当前系统是否证明 Context View 有价值

本次三组 evaluation case 不能直接证明 Context View 的价值，因为全部以 Text 模式运行，`workflow_state.context.items` 为空，Agent Context View 也为空。

本次可以证明的是：在没有 Context View 的情况下，当前五 Agent Workflow 仍能通过 Stage Artifact 完成信息传递。Context View 的价值需要通过 Structured 或 Auto Context case 另行验证。

### 当前系统是否证明 Stage Contract 有价值

可以证明。

主要证据：

- Agent1A 的 `specific_unknowns` 被 Agent1B 稳定转成澄清问题。
- Agent1B 的 `question_sources` 被 Agent2 用于 missing_info 和 risk_items。
- Agent2 的 `risk_items` 被 Agent3 转成风险相关验证关注点。
- Agent4 基本复用前序 Stage Artifact 汇总，没有重新生成问题。

Stage Contract 的价值尤其体现在 case_02 和 case_03：缺口、问题、风险和验证关注点形成了连续链路。

### 当前系统是否证明多 Agent 信息隔离有效

部分有效。

有效点：

- Agent1B 没有直接读取 Context，而是依赖 Agent1A Artifact。
- Agent3 的风险相关输出主要由 Agent2 风险结果驱动。
- Agent4 主要做汇总，没有明显承担新的分析职责。

仍存在的问题：

- case_01 暴露出 Agent1A 缺口边界偏宽，会把较完整需求中的实现细节也识别为 unknown。
- Agent2 会继承并放大 Agent1A 的偏宽 unknown，导致完整需求也产生较多风险。
- Text 模式没有 context_refs，无法验证 item 级来源追踪。

### 信息流设计效果判断

当前系统已经证明 Stage Artifact 是多 Agent 信息隔离的关键接口。它能让下游 Agent 不必重新理解全部输入，而是消费上游整理后的结构化结果。

但完整需求场景下，当前主要瓶颈不是 Agent 间传递失败，而是上游缺口判断标准偏宽。也就是说，问题更偏向 Stage Contract 的判定边界，而不是 Agent 架构错误。

### 后续评估建议

不需要新增 Agent。下一步如果继续评估，应使用同一批 case 增加 Structured Context / Human Context Compiler 输入版本，对比：

- context_refs 是否出现并可追踪。
- Agent1A 是否减少宽泛 unknown。
- Agent2 是否减少由实现细节引发的过量风险。
- Agent3 是否更多基于 related_rules / related_constraints 生成验证关注点。

本次不建议基于 Text 模式结果直接调整 Context View，因为本次没有实际使用 Context View。
