# Context Value Evaluation

> 文档状态：历史结果快照。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文中的数量指标只能作为人工评估证据，不能自动推出 Context 改善结论。

## Scope

本报告基于已有三个 evaluation case，比较三种输入版本对当前 Multi-Agent Workflow 的影响：

- Version A: Text only
- Version B: Structured Context
- Version C: Human Context Compiler 输出 Context

本次不评价代码实现质量，只评价信息流设计价值：Context View 是否改善 Agent1A 缺口识别、Agent2 风险结构化和 Agent3 验证关注点生成。

运行产物位于：

- `outputs/context_comparison/case_01_complete_requirement/`
- `outputs/context_comparison/case_02_incomplete_requirement/`
- `outputs/context_comparison/case_03_complex_rule_requirement/`
- `outputs/context_comparison/summary_metrics.json`

三组 case 的三个版本均完成 Workflow，Agent1A 到 Agent4 均成功执行。

## 1. Experiment Overview

| Case | 类型 | Version A | Version B | Version C |
|---|---|---|---|---|
| case_01_complete_requirement | 信息相对完整需求 | Text only | 手写 Structured Context | Human Context Compiler 输出 Context |
| case_02_incomplete_requirement | 信息明显不足需求 | Text only | 手写 Structured Context | Human Context Compiler 输出 Context |
| case_03_complex_rule_requirement | 规则复杂需求 | Text only | 手写 Structured Context | Human Context Compiler 输出 Context |

Version B 与 Version C 都通过现有 `local_structured_context` 链路进入 Workflow，因此下游流程相同。差异在于：

- Version B 是面向 Runtime 手写的 Context Package V2，包含更明确的 item 分类和部分 `applies_to`。
- Version C 是从人工维护 Markdown 经 Compiler 生成的 Context Package V2，来源追踪更完整，但当前缺少 action-level `applies_to`，unknown 更容易进入 `unassigned_unknowns`。

## 2. Agent1A Unknown Count Comparison

| Case | A Text only | B Structured Context | C Compiler Context | 观察 |
|---|---:|---:|---:|---|
| case_01_complete_requirement | 7 | 4 | 2 | Context 明显减少完整需求中的低价值 unknown |
| case_02_incomplete_requirement | 8 | 8 | 8 | 不完整需求中的真实 unknown 不应被减少，Context 主要提升来源追踪 |
| case_03_complex_rule_requirement | 3 | 3 | 3 | 三条未确认事项稳定保留，Context 没有错误消除真实缺口 |

### 2.1 case_01: 完整需求

Text only 下，Agent1A 生成 7 个 unknown，主要包括：

- 邮箱地址输入边界。
- 验证码生成规则。
- 验证码校验失败重试次数。
- 绑定成功响应结果。
- 短信验证码发送规则、有效期、重试限制。
- 新邮箱验证码校验是否与绑定时一致。
- 更换邮箱时是否检查新邮箱占用。

这些 unknown 中有一部分属于实现细节或低价值规则细节。Structured Context 后，unknown 降到 4 个；Compiler Context 后，unknown 降到 2 个。

结论：对信息相对完整的需求，Context View 能帮助 Agent1A 把已确认规则放入 known_conditions，从而减少把实现细节扩大为缺口的倾向。

### 2.2 case_02: 不完整需求

三种版本均保留 8 个 unknown：

- 验证方式未明确。
- 凭证有效期未明确。
- 验证失败处理未明确。
- 发送频率未明确。
- 未注册手机号是否允许登录未明确。
- 多账号绑定同一手机号如何处理未明确。
- 登录失败是否记录日志未明确。
- 操作日志字段未明确。

这是符合预期的。Context View 不应该消除真实缺口，而应该帮助系统确认这些缺口确实存在。

Version B 的优势在于 8 个 unknown 都带有 context_refs，并通过 `applies_to` 归属到对应 action。Version C 也保留 context_refs，但因为 Compiler 输出缺少 `applies_to`，这些 unknown 进入 `unassigned_unknowns`。

结论：Context View 对不完整需求的价值不是减少 unknown 数量，而是让 unknown 更可追踪、更可归属。

### 2.3 case_03: 复杂规则需求

三种版本均保留 3 个 unknown：

- 多张优惠券是否允许叠加使用。
- 订单金额变化后是否保留用户手动选择的优惠券。
- 优惠券不可用原因展示优先级。

Version B 中这些 unknown 被分配到具体 action，并保留 context_refs。Version C 中这些 unknown 进入 `unassigned_unknowns`。

结论：规则复杂场景下，Context View 没有减少真实业务决策缺口，但能增强规则保留和来源追踪。

## 3. Unknown Type Change

| Case | Version A 主要 unknown 类型 | Version B 变化 | Version C 变化 |
|---|---|---|---|
| case_01_complete_requirement | implementation detail gap + rule gap | 低价值实现细节减少，仍保留少量规则细节 | unknown 进一步减少，但以 unassigned 形式保留 |
| case_02_incomplete_requirement | business decision gap + rule gap + data/log gap | 类型不变，来源和动作归属增强 | 类型不变，来源增强但动作归属弱 |
| case_03_complex_rule_requirement | business decision gap + rule gap | 类型不变，动作归属和 context_refs 增强 | 类型不变，来源增强但动作归属弱 |

分类解释：

- business decision gap：需要业务确认的决策，例如是否允许未注册手机号登录、是否允许优惠券叠加。
- rule gap：规则缺失，例如验证方式、有效期、失败处理、展示优先级。
- constraint gap：限制条件缺失，例如权限、禁止行为、可用范围。
- implementation detail gap：实现细节缺失，例如页面入口、提示文案、字段格式、验证码长度。

本次最有价值的变化出现在 case_01：Context View 减少了部分 implementation detail gap 和低价值 rule gap。case_02 和 case_03 中，Context View 没有减少真实业务缺口，这是正确行为。

## 4. Agent2 risk_items Comparison

| Case | A risk_items | B risk_items | C risk_items | 观察 |
|---|---:|---:|---:|---|
| case_01_complete_requirement | 19 | 17 | 10 | Context 降低完整需求中的风险膨胀 |
| case_02_incomplete_requirement | 9 | 8 | 8 | 风险数量稳定，B/C 增加 context_refs |
| case_03_complex_rule_requirement | 7 | 10 | 8 | Context 让复杂规则触发更多具体边界风险 |

### 4.1 风险数量

case_01 中，Context 使 risk_items 从 19 降到 17，再到 10。这说明当 Context 明确说明规则时，Agent2 不再把所有细节缺失都放大为风险。

case_02 中，risk_items 从 9 降到 8。真实缺口仍然存在，所以风险不应大幅减少。

case_03 中，Structured Context 使 risk_items 从 7 增到 10。这不是退化，而是因为 Context 提供了更多规则边界，例如冻结账号、不可用券、金额变化、日志字段等，Agent2 能识别更多基于规则的风险。

### 4.2 风险类型

Version B 在 case_02 和 case_03 中保留了更稳定的风险类型：

- case_02: ambiguity / edge_case / performance / data。
- case_03: ambiguity / edge_case / permission / data。

Structured Context 让权限、数据、边界风险更容易从业务规则和限制中显式出现。

### 4.3 related_unknowns / related_rules / context_refs

Version A 没有 Context，因此 risk_items 的 context_refs 均为空。

Version B 中：

- case_02 的 8 个 risk_items 都能关联 Context unknown refs。
- case_03 的 3 个 unknown 风险能关联 Context unknown refs。
- related_rules 保留较好，能帮助 Agent3 理解风险背后的已知规则。

Version C 中：

- context_refs 能保留。
- 但由于 Compiler 输出缺少 `applies_to`，unknown 多进入 `unassigned_unknowns`。
- risk_items 的 related_rules 明显弱于 Version B。

结论：Context View 对 risk_items 的价值成立，但前提是 Context item 不仅有 source_ref，还要有足够的业务归属信息。只有 source_ref 不足以支撑高质量风险到规则的关联。

## 5. Agent3 Comparison

| Case | A Agent3 特征 | B Agent3 特征 | C Agent3 特征 | 判断 |
|---|---|---|---|---|
| case_01_complete_requirement | edge points 过多，风险关注偏泛化 | core points 更贴近规则，edge points 略减少 | 输出更收敛，但部分规则关联较弱 | Context 改善明显 |
| case_02_incomplete_requirement | 能覆盖缺口，但无来源 | 覆盖缺口且保留 Context refs | 覆盖缺口，但 action 归属弱 | Context 改善可追踪性 |
| case_03_complex_rule_requirement | 能生成基本验证点 | 明显增加基于规则的验证关注点 | 规则覆盖较多，但来源到动作链路弱 | Context 提升规则型验证质量 |

### 5.1 是否生成更准确验证关注点

case_01 中，Context 让 Agent3 从大量泛化边界关注点，转向更多基于邮箱唯一、验证码有效期、发送频率、登录限制、日志字段等已知规则的验证点。

case_03 中，Structured Context 显著提高了规则型验证点数量。Version B 的 core_test_points 和 acceptance_criteria 增加，说明 Agent3 能使用 Context 中的业务规则生成更完整的验证关注点。

### 5.2 是否依赖 risk_items

三种版本中，Agent3 输出都能对应 Agent2 risk_items。Version B/C 中 risk_items 带 context_refs，使 Agent3 的来源链路更清晰。

但 Version C 的 related_rules 较弱，说明仅靠 Compiler 输出的 source_ref 还不够，Agent3 仍更依赖 Agent2 的 risk_items 描述本身。

### 5.3 是否减少泛化测试点

case_01 中有改善。Version A 的 edge_test_points 较多，且包含不少实现细节关注。Version B/C 更收敛。

case_03 中没有减少，反而增加了规则型测试关注点。这是合理结果：复杂规则场景下 Context 的价值不是减少输出，而是让输出覆盖更多真实规则边界。

## 6. Trace and Context Consumption

Version A 没有 Context consumption。

Version B/C 的 trace 均显示 Context View 被 Agent1A、Agent2、Agent3、Agent4 消费：

- Agent1A 消费 facts / rules / constraints / flows / unknowns，用于第一次理解和缺口识别。
- Agent2 消费 rules / constraints / unknowns，用于风险判断。
- Agent3 消费 rules / constraints / flows / unknowns，并优先使用 risk_items。
- Agent4 消费 Context source summary，用于汇总和复核。

关键差异：

- Version B 的手写 Context 中存在更明确的 `applies_to`，unknown 能分配到具体 action。
- Version C 的 Compiler 输出保留了完整 source_ref，但缺少 `applies_to`，unknown 多进入 unassigned。它仍能被 Agent1B 提问，但对 Agent2 的 related_rules 关联较弱。

这说明 Context View 的有效性不仅取决于“有没有上下文”，还取决于 item 是否具备可消费的业务归属信息。

## 7. Overall Judgment

### 7.1 Context View 是否提升 Workflow 效果

结论：提升了，但不是无条件提升。

Context View 的正向价值已经体现：

- 在完整需求中减少低价值 unknown 和风险膨胀。
- 在不完整需求中保留真实 unknown，并提供 context_refs。
- 在复杂规则需求中增强 known_conditions、risk_items 和规则型验证关注点。
- 让 Agent1A -> Agent1B -> Agent2 -> Agent3 的 Stage Contract 更可追踪。

### 7.2 Structured Context 与 Compiler Context 的差异

Structured Context 效果更稳定，因为它可以直接提供：

- 正确 section 分类。
- item 级 source_ref。
- action-level `applies_to`。

Compiler Context 的价值是降低人工手写 JSON 成本，并提供完整 source_ref。但当前对动作归属支持不足，导致：

- unknown 进入 `unassigned_unknowns`。
- Agent1B 仍能提问，但问题缺少 action 归属。
- Agent2 risk_items 的 related_rules 关联弱于手写 Structured Context。

因此，Compiler Context 适合作为降低人工维护成本的入口，但要达到 Structured Context 的效果，需要补足业务归属信息，而不是只完成格式转换。

### 7.3 Context View 对三类 case 的价值边界

| 场景 | Context View 主要价值 | 不应期待的效果 |
|---|---|---|
| 完整需求 | 减少低价值 unknown，降低风险膨胀 | 不应消除所有实现细节问题 |
| 不完整需求 | 保留真实 unknown，并提供来源和归属 | 不应替用户补全业务决策 |
| 复杂规则需求 | 增强规则保留和验证覆盖 | 不一定减少输出数量 |

## 8. Final Answer

Context View 确实提升了 Workflow 效果，尤其体现在信息来源可追踪、已知规则保留、真实 unknown 区分和风险到验证的传递上。

但本次实验也说明：Context View 的价值不是“给 Agent 更多文本”，而是给 Agent 经过边界控制的结构化信息。最关键的不是 Context 数量，而是：

- section 分类是否准确；
- unknown 是否只表达真实未确认事项；
- source_ref 是否保留；
- applies_to 是否能支撑动作归属；
- Stage Artifact 是否继续承接这些信息。

因此，当前信息流设计方向成立。最强结果来自 Version B 手写 Structured Context；Version C Human Context Compiler 降低了人工 JSON 维护成本，但如果缺少 `applies_to`，效果会弱于手写 Structured Context。

最终判断：Context View 有明确信息流价值，但要真正稳定提升 Workflow，需要保持“结构化、可追踪、可归属”的 Context，而不是简单增加上下文内容。

## 9. P0 Follow-up: Compiler `applies_to` Support

基于以上结论，已完成 P0 最小改造：Human Context Compiler 支持在人工维护 Markdown 列表项中通过内联属性声明业务动作归属。

支持格式：

```text
- 未确认事项文本 | applies_to: 动作1; 动作2
- 规则文本 | applies_to_candidates: 动作1; 动作2
```

该能力不新增 Context 类型，不改变 Runtime Context V2，也不改变五 Agent Workflow。Compiler 只把人工模板中的归属信息编译进已有 Context item 字段。

### P0 Validation Result

P0 后只重跑 Version C: Human Context Compiler 输出 Context。

运行产物位于：

- `outputs/context_comparison_p0/case_01_complete_requirement/C_compiler_context/`
- `outputs/context_comparison_p0/case_02_incomplete_requirement/C_compiler_context/`
- `outputs/context_comparison_p0/case_03_complex_rule_requirement/C_compiler_context/`
- `outputs/context_comparison_p0/summary_metrics.json`

| Case | 指标 | P0 前 | P0 后 |
|---|---|---:|---:|
| case_01_complete_requirement | unassigned_unknowns | 2 | 0 |
| case_01_complete_requirement | assigned alignment | 0 | 2 |
| case_01_complete_requirement | risk_items related_rules | 0 | 4 |
| case_02_incomplete_requirement | unassigned_unknowns | 8 | 0 |
| case_02_incomplete_requirement | assigned alignment | 0 | 8 |
| case_02_incomplete_requirement | risk_items related_rules | 0 | 4 |
| case_03_complex_rule_requirement | unassigned_unknowns | 3 | 0 |
| case_03_complex_rule_requirement | assigned alignment | 0 | 3 |
| case_03_complex_rule_requirement | risk_items related_rules | 0 | 12 |

### P0 Conclusion

P0 验证了此前判断：Compiler Context 效果弱于手写 Structured Context 的主要原因不是 Compiler 路径本身，而是缺少业务动作归属。

加入轻量 `applies_to` 后：

- Agent1A 能把 Compiler unknown 分配回具体 action。
- Agent1B 继续基于 specific_unknowns 生成问题，不再依赖 unassigned fallback。
- Agent2 的 risk_items 开始恢复 related_rules。
- Agent3 后续消费 risk_items 时能获得更清晰的规则和 unknown 关联。

因此，Human Context Compiler 可以作为主输入方向继续保留。下一步不应扩展 Auto Context，而应继续控制在人工可维护模板到 Runtime Context 的编译质量上。
