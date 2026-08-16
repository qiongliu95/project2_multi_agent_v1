# Multi-Agent 需求分析系统架构复盘

本文以技术负责人视角，对当前 Multi-Agent 需求分析系统做架构复盘。目标是判断当前系统真实问题和下一步是否需要优化，而不是设计新系统。

约束：

- 不扩展 RAG、知识库、知识图谱、企业知识治理。
- 不新增 Agent。
- 不改变五 Agent 主流程定位。
- 不把 Context 能力本身作为目标。
- 先列事实，再给判断。

## 一、当前 Structured Context 设计评审

### 事实

当前系统已经支持 `Structured Context V2`，核心字段包括：

- `confirmed_facts`
- `business_rules`
- `constraints`
- `process_flows`
- `unknowns`

代码链路上，Structured Context V2 通过 `local_structured_context` 进入 Workflow：

```text
Context Package V2 JSON
-> read_local_structured_context
-> workflow_state.context.items
-> build_agent_context_view(agent_id)
-> rendered_agent_input
-> Agent1A/1B/2/3/4
```

当前 Agent Context View 的 section 分发是：

| Agent | 当前消费 section |
|---|---|
| Agent1A | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns` |
| Agent1B | `confirmed_facts`, `business_rules`, `constraints`, `unknowns` |
| Agent2 | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns`, `quality_flags` |
| Agent3 | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns` |
| Agent4 | `confirmed_facts`, `business_rules`, `constraints`, `process_flows`, `unknowns`, `source_refs`, `quality_flags` |

Structured Context V2 的优点已经被验证：

- 能让 Agent 看到明确的业务规则、限制、流程和 unknown。
- 能通过 item id 和 source_ref 做消费追踪。
- 能减少 Markdown 全文进入 Agent1A 后被一次性压缩造成的信息损失。
- 能让 Agent1A/Agent1B 更容易区分已知规则和具体待确认项。

### 判断

Structured Context V2 适合作为 Agent Runtime 输入格式，但不适合作为人工长期维护格式。

原因：

| 维度 | 判断 |
|---|---|
| 产品人员是否容易维护 | 不容易。产品人员通常按功能、流程、角色、规则讨论，不会自然按 `confirmed_facts/business_rules/constraints` 分类维护 |
| 测试人员是否容易维护 | 不容易。测试人员更自然维护风险、异常场景、验证关注点，而不是把测试经验拆成 Runtime section |
| 是否需要人工额外整理历史需求文档 | 是。当前手写 V2 等于要求人工先读历史文档，再拆 item、分类、写 id、写 source_ref |
| 是否把人工工作转变成填写 Schema | 是。它降低了 Agent 输入混乱，但把整理成本转移给了人 |
| 是否适合作为当前 Workflow 输入 | 适合。Runtime 层清晰，Agent View 和 Trace 都能稳定消费 |

结论：

- `Structured Context V2` 应保留为机器消费层。
- 不应要求产品/测试人员直接维护 V2 JSON。
- 如果继续让人工手写 V2，系统会从“降低需求分析成本”变成“要求人工先做一次结构化整理”。

## 二、人工维护成本分析

### 事实

真实企业通常已经存在历史需求文档、设计说明、Bug 记录、测试记录。它们的形态往往是：

- PRD / Markdown / Word / Wiki 页面。
- Issue / Bug 单。
- 测试用例或测试记录。
- 评审纪要。

这些资料天然按业务模块、功能场景、版本、问题单组织，而不是按 AI Runtime Schema 组织。

当前系统的三条上下文路径对人工要求不同：

| 路径 | 人工需要做什么 | 系统做什么 |
|---|---|---|
| Markdown Context | 人工挑选并提供相关 Markdown | 系统读取 Markdown，主要拼给 Agent1A |
| Structured Context V2 | 人工整理成 JSON，拆分 facts/rules/constraints/flows/unknowns | 系统读取、分发、Trace |
| Auto Context | 人工提供历史资料目录并审核候选 | 系统索引、关键词召回、规则抽取、生成 review queue 和 consumable context |

### 判断

如果企业已经存在历史需求文档，不应要求人工把全部历史资料重新整理成 Structured Context。

三个选项的判断：

| 选项 | 是否推荐 | 原因 |
|---|---|---|
| A. 重新整理成 Structured Context | 不推荐作为常规流程 | 成本高，容易把产品/测试变成 Schema 维护者，只适合少量基准样例或关键模块 |
| B. 直接提供历史需求文档，由系统辅助提取 | 推荐作为主方向，但必须带人工审核 | 符合真实企业工作流，系统承担检索和候选整理，人工承担业务确认 |
| C. 其他方式 | 推荐轻量组合：人工提供原始资料和当前需求，系统生成候选，人工审核后进入 V2 Runtime | 既不要求全自动，也不要求人工手写 JSON |

人工应该承担：

- 确认规则是否当前有效。
- 判断冲突版本。
- 判断某条历史信息是否适用于当前需求。
- 决定风险是否需要接受、规避或补需求。
- 对关键输出做业务判断。

系统应该承担：

- 读取历史资料。
- 找到可能相关内容。
- 保留来源位置。
- 初步分类为规则、限制、流程、unknown 候选。
- 把候选组织成审核队列。
- 审核通过后转换成 Agent Runtime 输入。
- 记录 Agent 消费了哪些 Context item。

当前不应假设人工愿意额外维护大量数据。有效的方向是减少人工找资料和整理格式的成本，而不是增加一套长期手写 JSON 工作。

## 三、Auto Context 方向评估

### 事实

当前 Auto Context 代码流程是：

```text
data/history Markdown/TXT
-> build_context_index
-> retrieve_context_candidates
-> build_review_queue
-> review
-> build_consumable_context
-> local_structured_context
-> Workflow
```

当前实际使用的匹配方式：

- 固定关键词列表。
- chunk 文本打分。
- metadata scope / effective_status / trust。
- top_k 截断。
- 没有 embedding。
- 没有向量库。
- 没有 LLM 语义检索。

候选生成方式：

- 按行抽取。
- 用字符串规则判断 section。
- 用规则检测少量冲突。
- 生成 review queue。
- 只有 `source_verified=true`、`human_confirmed=true`、`review_status=approved`、`version_status=active`、`conflict_status=none`、`scope_status=matched` 的 item 才能进入 consumable context。

已经暴露的问题：

- 自动分类不稳定。
- 召回和抽取质量依赖历史资料写法。
- 需要 gold label 或人工审核验证，不能只相信系统自己的状态字段。
- 规则越多，维护成本越高。
- 如果继续追求自动生成完整 Context Package，复杂度会快速上升。

### 判断

Auto Context 当前解决的首要问题是“减少人工整理上下文”，其次才是“提高需求分析质量”。

它对质量的提升是间接的：

- 找到相关历史规则后，Agent 能更具体。
- 但如果召回错误、分类错误或冲突漏检，反而会污染分析。

它引入的问题：

| 问题 | 影响 |
|---|---|
| 系统复杂度增加 | 需要索引、召回、抽取、审核、build、评估多个阶段 |
| 错误分类 | 规则、事实、流程、unknown 混淆会影响 Agent1A/Agent1B |
| 验证成本 | 必须有人审核，且需要独立 gold label 评估错误放行 |
| 维护成本 | 关键词、冲突规则、分类规则会随业务域增长而膨胀 |
| 误用风险 | 容易被误解为“自动生成企业知识”，超出当前项目目标 |

是否应该继续投入：

- 不应继续投入“全自动生成完整 Context Package”。
- 可以保留轻量 Auto Context 作为辅助候选生成工具。
- 投入边界应限制在“减少人工找资料和初步整理成本”，不能追求替代业务判断。

当前最合理判断：

```text
Auto Context 可以保留，但不应成为下一阶段主战场。
如果继续做，只优化错误放行、来源追踪、审核体验和低成本召回。
不要扩展成自动知识治理。
```

## 四、上下文进入 Workflow 的信息流分析

### 事实：Text 模式

```text
requirement_text
-> Workflow State
-> plain rendered_agent_input
-> Agent1A
-> Agent1B
-> Agent2
-> Agent3
-> Agent4
```

消费情况：

| Agent | 实际消费 |
|---|---|
| Agent1A | 原始需求文本 |
| Agent1B | 原始需求文本 + Agent1A main_flow/action_gap_candidates |
| Agent2 | 原始需求文本 + Agent1A + Agent1B |
| Agent3 | 原始需求文本 + Agent1A + Agent2 |
| Agent4 | 原始需求文本 + Agent1A/1B/2/3 |

问题：

- 没有历史上下文。
- 风险分析只能基于当前文本和上游推理。
- 缺口可能偏宽泛。

### 事实：Markdown Context 模式

```text
local_markdown
-> read_local_markdown_context
-> workflow_state.context.items
-> build_context_augmented_requirement
-> Agent1A
-> Agent1A output
-> Agent1B/2/3/4
```

实际特点：

- Markdown 原文主要拼接给 Agent1A。
- Agent1B/2/3/4 不直接消费 Markdown item 级结构。
- 下游看到的是 Agent1A 对 Markdown 的压缩结果。

问题：

- 信息可能在 Agent1A 压缩时丢失。
- Markdown 没有稳定 item id，无法形成 item 级 context_consumption。
- Agent1A 如果没有抽出某条规则，下游通常无法恢复。
- 信息来源可以在 Tool Trace 看到，但业务结论不稳定保留来源。

### 事实：Structured Context V2 模式

```text
local_structured_context JSON
-> read_local_structured_context
-> workflow_state.context.items
-> build_agent_context_view(agent_id)
-> build_rendered_agent_input
-> Agent
```

实际特点：

- 每个 Agent 有独立 Context View。
- 原始 requirement_text 不被覆盖。
- Trace 记录 `context_view`、`context_consumption` 和 `final_input_sources`。
- Structured Context 中的 unknown 可被 Agent1A 转成 `specific_unknowns`。

问题：

- Runtime 输入清晰，但人工维护成本高。
- Agent 业务输出不强制携带 source_ref。
- `process_flows` 当前不进入 Agent1B，部分流程类已知信息可能只依赖 Agent1A 压缩传递。
- 历史 Bug 和历史测试经验没有一等输入位置，只能混入普通 Context 时被模型阅读。

### 事实：Auto Context 模式

```text
history docs
-> index
-> retrieval
-> review queue
-> human review
-> consumable Context Package V2
-> local_structured_context
-> Structured Workflow
```

实际特点：

- 未审核候选不会进入 Agent Context View。
- 审核后的 consumable package 复用 Structured Context 路径。
- required context 失败时 Workflow 停止，Agent 不执行。

问题：

- 自动召回和分类质量不稳定。
- 审核前的候选与 Agent 完全隔离，这是正确的，但也意味着 Auto Context 的价值必须通过审核效率证明。
- 如果历史资料本身不完整，自动结果也不会完整。

### 判断：当前信息流问题

| 问题 | 具体表现 | 影响 |
|---|---|---|
| 信息重复 | Structured 模式下多个 Agent 都能看到部分相同规则和 unknown | 可接受，当前规模不大；但长上下文下会增加噪声 |
| 上游压缩导致信息丢失 | Markdown 主要由 Agent1A 压缩后传下游 | 是当前 Markdown 路径最大问题 |
| Agent 拿不到需要的信息 | Agent2 缺少历史风险模式；Agent3 缺少历史验证经验；Agent1B 不直接消费 process_flows | 会限制风险识别和验证关注点质量 |
| Context 与 Agent 职责不匹配 | Structured V2 更适合 Runtime，不适合人工维护；历史 Bug/测试经验不应混入 business_rules | 会导致维护成本和语义污染 |
| 来源没有进入最终业务结论 | Trace 有 source_ref，但 Agent2/3/4 输出不强制带来源 | 人工复核仍需翻 Trace |

当前问题不是五 Agent 架构错误，而是上下文准备成本、信息分发边界和阶段输出契约的问题。

## 五、下一步最小优化方向

### P0：必须优化的问题

| 优化 | 解决什么实际问题 | 减少什么人工成本 | 提高什么 Agent 效果 | 是否需要修改五 Agent 架构 |
|---|---|---|---|---|
| 停止把 Structured Context V2 当作人工主维护格式 | 避免产品/测试人员长期手写 Runtime JSON | 减少拆 item、分类、写 id/source_ref 的格式劳动 | 间接提高。人工更愿意提供真实上下文，输入质量更稳定 | 不需要 |
| 保持 Markdown/历史文档作为人工主要输入，系统只做辅助提取和审核队列 | 避免要求人工重写已有历史文档 | 减少重新整理历史资料的成本 | 提高 Agent1A/2 的上下文覆盖率，但依赖审核 | 不需要 |
| 收敛 Auto Context 的边界：只做候选生成，不做全自动事实放行 | 防止错误分类和冲突规则污染 Agent | 减少人工初筛，但保留关键审核 | 提高输入安全性，避免 Agent 基于错误事实分析 | 不需要 |
| 强化现有信息流复盘和样本验证 | 当前只有少量样例，无法证明真实收益 | 避免投入到无价值复杂能力 | 用真实样本判断 Agent1B 问题、Agent2 风险是否真的改善 | 不需要 |

### P1：有价值但不是必须的问题

| 优化 | 解决什么实际问题 | 减少什么人工成本 | 提高什么 Agent 效果 | 是否需要修改五 Agent 架构 |
|---|---|---|---|---|
| 对 Structured Context 人工维护方式做轻量模板化 | 降低人工输入门槛 | 减少手写 JSON 和字段遗漏 | 提高 Context 输入稳定性 | 不需要 |
| 优化 Agent1B 可见信息边界，例如流程类已知信息如何避免重复提问 | 某些已知流程被压缩后仍可能被追问 | 减少人工处理无效澄清问题 | 提高澄清问题精度 | 不需要 |
| 在最终输出中更清楚暴露关键来源引用 | 当前 source_ref 主要在 Trace 中 | 减少人工复核时翻 Trace 的成本 | 提高结果可信度和可审计性 | 不需要 |
| 小范围评估历史 Bug/测试经验如何作为输入材料 | 当前 Agent2/3 缺少这类经验 | 减少测试人员反复翻历史问题 | 可能提高风险识别和验证关注点质量 | 不需要改架构，但可能需要输入契约小调整 |

### P2：暂时不要做的问题

| 方向 | 解决什么实际问题 | 减少什么人工成本 | 提高什么 Agent 效果 | 是否需要修改五 Agent架构 | 为什么暂时不要做 |
|---|---|---|---|---|---|
| 完整自动生成 Context Package | 不稳定 | 不确定，可能增加审核成本 | 不稳定，错误事实会污染结果 | 不需要但复杂度高 | 当前分类和召回质量不足，容易把 Context 变成目标 |
| 大规模多数据源接入 | 不直接解决当前最小问题 | 不确定 | 不确定 | 不需要但外围复杂度高 | 单一 Markdown/TXT 质量问题尚未收敛 |
| RAG 平台 | 超出当前目标 | 短期不明确 | 不明确 | 可能引入新架构 | 当前是需求分析辅助工具，不是知识检索平台 |
| 企业知识库/知识图谱 | 超出当前目标 | 长期可能，但短期成本高 | 不明确 | 会改变系统定位 | 投入产出比低 |
| 新增 Agent 或动态 Agent 路由 | 当前没有证据表明 Agent 数量不足 | 不减少人工成本 | 不一定提高效果 | 会修改架构 | 当前问题主要是输入和契约，不是 Agent 编排 |
| 自动测试平台 | 偏离目标 | 不减少需求分析成本 | 会把 Agent3 推向测试资产生产 | 可能改变职责 | 当前 Agent3 应保持验证关注点 |

## 六、复盘结论

### 事实总结

1. 当前五 Agent Workflow 已能完成需求解析、澄清问题、风险分析、验证关注点和总结。
2. Text 模式稳定但缺少历史上下文。
3. Markdown 模式降低了接入门槛，但信息主要在 Agent1A 被压缩，下游 item 级可追踪不足。
4. Structured Context V2 提升了 Runtime 输入质量，但不适合人工长期维护。
5. Auto Context 能减少部分人工整理，但当前匹配和分类仍是轻量规则，质量依赖审核。
6. 当前最大风险不是能力不够，而是继续增加复杂系统，偏离“辅助需求分析和风险识别”的目标。

### 判断

当前系统已经验证了核心技术链路：外部上下文可以进入固定五 Agent Workflow，并影响缺口识别和风险分析。

但产品价值还没有完全验证：尚未证明在真实企业场景中，系统能稳定减少产品/测试人员的需求分析耗时，并稳定提升风险识别质量。

下一步不应该扩展新系统，而应该以最低复杂度解决两个问题：

1. 不再要求人工维护机器 Schema。
2. 保持历史文档输入和审核机制，让系统承担查找、候选整理和来源追踪，人工只承担业务判断。

最终结论：

```text
当前系统不需要新增 Agent，也不需要 RAG、知识库或知识图谱。
下一步应停止扩展基础架构，转向验证“更低人工整理成本 + 更稳定上下文输入”是否真正改善需求分析和风险识别。
```
