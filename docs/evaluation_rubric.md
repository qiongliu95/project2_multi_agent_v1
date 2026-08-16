# Human Evaluation Rubric

> 文档状态：评分维度参考。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文保留为人工评分参考，不单独给出结项结论。

## 目的

本文定义人工如何评估开放式 Multi-Agent Workflow 输出。

本项目不使用唯一 Golden Answer。LLM 输出可以存在表达差异、颗粒度差异和合理顺序差异，但必须满足当前任务目标，并且不能编造事实或越过 Agent 职责边界。

每个 case 应继续使用：

- `must_cover`
- `valid_optional`
- `unsupported`

## 统一评分锚点

六个 Criteria 均使用同一套基础评分含义：

| 分数 | 统一含义 |
|---:|---|
| 2 | 核心要求基本满足，仅有轻微问题，不影响主要结果。 |
| 1 | 存在明确实质问题，但核心能力仍存在，结果仍可部分使用。 |
| 0 | 核心能力缺失，或问题已导致主要输出不可信/不可用。 |
| N/A | 当前 case 不适用，需在 notes 中说明原因。 |

评分本身不会自动创建 Failure Type。评审者必须明确标记 confirmed failure。

## 避免重复处罚

同一个问题可以同时成为多个 Criteria 的证据，但不能机械地在多个维度重复扣分。

如果同一个问题影响多个维度，评审者必须分别说明它对每个维度造成的具体影响。例如：

- 一个无依据规则会影响 Grounding，因为它没有来源。
- 如果该规则还导致 Agent3 生成不可执行验证点，才影响 Usefulness。
- 如果它只是措辞不佳，但不改变结论，不应额外扣 Boundary 或 Completeness。

六个 Criteria 的判定边界如下：

| Criteria | 主要判断 |
|---|---|
| Grounding | 有没有依据。输出是否基于 requirement、Context View 或 Stage Artifact。 |
| Boundary Compliance | 是否超出当前 Agent 或当前任务范围。 |
| Completeness | 明确需求、must_cover 或关键 Stage Artifact 是否被遗漏。 |
| Uncertainty Handling | 未知信息是否被保留、澄清或标记，而不是伪造成事实。 |
| Relevance | 输出是否聚焦当前需求、当前业务对象和当前流程。 |
| Usefulness | 结果是否能支持产品/测试人员下一步工作。 |

低分不等于必须修改。是否修改取决于问题是否阻塞核心业务事实、关键流程或主要输出的可信性。

## 评估维度

### 1. 依据性（Grounding）

问题：输出是否基于 requirement text、Context View 或 Stage Artifact。

判定说明：

- 2：主要结论均有来源，少量表达不精确不影响判断。
- 1：存在无依据或来源弱的结论，但主要结论仍可追溯。
- 0：大量关键事实无依据，或错误引用导致主要输出不可信。

良好行为：

- 只有在 requirement 或 context 中出现时，才使用已知业务规则。
- 在可用时保留来源引用。
- 不编造重试次数、时间限制、阈值或策略。

失败候选：

- 输出陈述了无依据事实。
- 输出引用的 context item 不能支持对应结论。

### 2. 边界遵守（Boundary Compliance）

问题：每个 Agent 是否停留在自己的职责范围内。

判定说明：

- 2：基本遵守 Agent 职责，仅有轻微措辞越界。
- 1：出现明确越界，但主要阶段职责仍成立。
- 0：越界行为主导输出，导致该阶段结果不可用。

预期边界：

| Agent | 职责 | 不负责 |
|---|---|---|
| Agent1A | requirement structure、known conditions、specific unknowns、context refs | risk solution、test design |
| Agent1B | 基于 Agent1A artifact 生成 clarification questions | 重新阅读完整 context、发明新需求 |
| Agent2 | 基于 artifacts 和 context 做 risk identification | 解决风险、定义业务规则 |
| Agent3 | 基于 risks 和 rules 生成 validation focus | 风险分析、最终业务决策 |
| Agent4 | aggregation 和 human review summary | 重新分析 raw context 并生成新结论 |

### 3. 完整性（Completeness）

问题：输出是否覆盖当前 case 的 `must_cover` 项。

判定说明：

- 2：核心 must_cover 基本覆盖，仅遗漏非关键细节。
- 1：遗漏明确重要内容，但仍保留部分核心分析能力。
- 0：关键流程、关键 unknown 或主要风险缺失，导致结果不可用。

良好行为：

- main flow 覆盖关键用户/系统动作。
- 缺失信息被表达为 specific unknowns。
- risk items 覆盖主要需求缺口。
- validation points 反映已识别风险和规则。

失败候选：

- must-cover 的业务规则、unknown 或 risk 在没有解释的情况下缺失。

### 4. 不确定性处理（Uncertainty Handling）

问题：输出是否保留 unknown 的不确定性。

判定说明：

- 2：unknown 被正确保留、澄清或转为风险关注点。
- 1：部分 unknown 处理不充分，但没有系统性伪造成事实。
- 0：关键 unknown 被当作确定规则，导致主要输出不可信。

良好行为：

- unknown 被转化为 clarification questions 或 risk concerns。
- unknown 不被转化为 confirmed rules。
- 基于 unknown 的 validation points 表达为待确认或需要关注的事项。

失败候选：

- 模型把“未确定”写成确定行为。
- 模型为 unknown 编造解决方案。

### 5. 相关性（Relevance）

问题：gap、risk 和 validation point 是否与当前需求相关。

判定说明：

- 2：输出基本聚焦当前 feature、role、workflow、rules 和 constraints。
- 1：存在明显泛化或偏题内容，但主要输出仍相关。
- 0：大量输出偏离当前需求，主要结果不可用。

良好行为：

- 聚焦当前 feature、user role、workflow、rules 和 constraints。
- 忽略无关 context。

失败候选：

- 增加来自无关功能的泛化风险。
- 在没有 requirement 或 context 支持的情况下扩展到安全、合规或实现主题。

### 6. 有用性（Usefulness）

问题：产品经理或测试人员是否可以用输出继续分析。

判定说明：

- 2：结果清晰、可复核、能直接支持下一步澄清、风险复核或验证设计。
- 1：结果有实质问题，但仍可提取部分有效信息继续使用。
- 0：输出泛化、不可执行或误导性强，无法支持下一步工作。

良好行为：

- questions 可直接回答。
- risks 足够具体，能被人工复核。
- validation points 能指导实际测试关注点。

失败候选：

- 输出泛化、重复或过于抽象，无法行动。

## Overall 与 Blocking

人工评估需要分别填写：

- `Overall`: `Pass` / `Partial` / `Fail`
- `Blocking`: `Yes` / `No`

Overall 不通过六项简单平均分或总分机械计算。

建议判断：

| Overall | 含义 |
|---|---|
| Pass | 核心目标基本满足，问题不影响主要使用。 |
| Partial | 存在明确问题，但仍可部分使用，且不一定需要修改。 |
| Fail | 主要输出不可依赖，或核心能力未体现。 |

Blocking 不等于低分。Blocking 重点判断问题是否已经导致核心业务事实、关键流程或主要输出不可依赖、无法继续使用。

建议判断：

| Blocking | 含义 |
|---|---|
| Yes | 问题阻塞当前证据进入后续评估或结项判断，需要先处理。 |
| No | 问题可记录为模型波动、表达质量、颗粒度差异或 Known Limitation。 |

示例：

- 某个维度为 1，但结果仍可用：通常是 `Blocking=No`。
- Grounding 为 0，且关键事实被编造：通常是 `Blocking=Yes`。
- Usefulness 为 1，因为表达不够自然：通常是 `Blocking=No`。

## 与自动检查的关系

自动检查可以生成候选信号，交给人工复核。

示例：

- possible unsupported fact
- possible broad question
- possible unknown-as-fact
- possible irrelevant risk

这些信号的状态是 `review_required`，不是失败。是否成为 confirmed Failure Type 由人工评审决定。
