# Human Context Model 可维护性评审

> 文档状态：Experimental / Candidate。
>
> 本文讨论人工维护上下文的候选形态，不代表当前冻结 Workflow 要新增 Context 层或改变 Agent1B indirect-only Context visibility。

本文基于当前 `Context Compiler Design Review`，从真实产品经理和测试人员的工作方式出发，评审 Human Context Model 是否适合作为长期人工维护格式。

本文不考虑技术实现，不修改代码，不扩展 RAG、知识库、Agent 平台或自动文档理解能力。

## 一、字段可维护性评审

Human Context Model 的核心判断标准不是“能否编译成 Context Package V2”，而是：

- 产品人员是否能自然维护。
- 测试人员是否能自然补充。
- 是否能支撑 Agent 风险分析。
- 是否能降低需求分析成本。
- 是否避免让人工承担机器 Schema 整理工作。

### 字段逐项判断

| 字段 | 是否符合业务维护习惯 | 是否应人工维护 | 是否可自动生成 | 是否应拆到其他 Context | 评审结论 |
|---|---|---:|---:|---:|---|
| 功能目标 | 高。产品人员通常按“这个功能解决什么问题”描述 | 是 | 可辅助草拟 | Business Context | 必须保留。它是模块级上下文入口，但不应写成过细规则 |
| 业务对象 | 高。账号、手机号、验证码、订单等对象是业务讨论核心 | 是 | 可辅助提取 | Business Context | 必须保留。对象决定规则、权限、状态和风险边界 |
| 用户角色 | 高。角色影响流程、权限和验收 | 是 | 可辅助提取 | Business Context | 必须保留。角色缺失会直接影响 Agent2 的权限风险 |
| 前置条件 | 中。业务人员会描述，但经常遗漏 | 建议人工维护 | 可从流程/规则推导候选 | Business Context | 建议保留，但不要强制每个模块都完整填写；缺失时进入未确认事项 |
| 主流程 | 高。真实需求评审通常围绕流程展开 | 是 | 可辅助整理 | Business Context | 必须保留。应按步骤维护，而不是维护成一句长文本 |
| 业务规则 | 高。产品/测试都能理解 | 是 | 可从文档候选生成，但必须确认 | Business Context | 必须保留。业务规则是进入 Agent 的最高价值信息之一 |
| 限制条件 | 高。禁止、只读、不可直接修改等容易维护 | 是 | 可辅助提取 | Business Context | 必须保留。限制条件直接影响风险和测试点 |
| 异常场景 | 高，对测试人员尤其自然 | 建议人工维护 | 可从 Bug/测试资产辅助生成 | Business Context 或 Risk Context | 应保留，但要区分“已定义异常处理”和“潜在风险场景” |
| 风险关注点 | 中高。测试人员更容易维护，产品人员可维护优先级 | 建议人工维护 | 可从历史 Bug 辅助生成 | Risk Context | 不应混在 Business Context 的规则里，应拆到 Risk Context |
| 历史问题 | 高，对测试/研发自然，对产品可读即可 | 建议人工维护或审核导入 | 可从 Bug 系统导入候选 | Risk Context | 应拆到 Risk Context。历史问题不是业务事实 |
| 验证关注点 | 高，对测试人员自然，产品可作为验收参考 | 建议人工维护 | 可从测试用例/经验导入候选 | Validation Context | 应拆到 Validation Context。不要污染需求事实 |
| 未确认事项 | 高。需求评审天然会维护待确认问题 | 是 | 可辅助发现 | Business Context，必要时关联 Risk/Validation | 必须保留。它是减少重复提问和聚焦澄清问题的关键 |

### 关键判断

当前字段整体合理，但不应全部放在一个平铺的“业务上下文”文档中长期维护。

更合理的方式是：

- 产品人员主要维护 Business Context。
- 测试人员主要维护 Risk Context 和 Validation Context。
- 系统负责把三类上下文编译为 Agent Runtime 可消费结构。

这样能避免一个文件同时承担“业务事实、风险经验、测试经验”三种职责，降低长期维护混乱。

## 二、是否应拆成 Business / Risk / Validation Context

建议拆分，但不是为了增加架构复杂度，而是因为三类信息的维护人、用途、更新频率和可信边界不同。

### 为什么拆

| 原因 | 不拆的风险 | 拆分后的收益 |
|---|---|---|
| 维护角色不同 | 产品和测试都在同一个上下文里混写，职责不清 | 产品维护业务规则，测试维护风险和验证经验 |
| 信息性质不同 | 历史 Bug 被误当作业务规则，测试经验被误当作需求事实 | 规则、风险、验证经验边界清晰 |
| 更新频率不同 | 业务规则版本变更会和测试经验补充互相干扰 | 各类上下文可独立更新 |
| Agent 消费不同 | Agent1A 可能消费到不该消费的历史 Bug 或测试点 | Agent1A 消费业务事实；Agent2/3 消费经验材料 |
| 审核标准不同 | 所有内容都按“业务规则确认”审核，成本高 | 业务规则确认、风险适用性确认、验证复用确认分开 |

### 推荐拆分

```text
Human Maintained Context
├─ Business Context
│  ├─ 功能目标
│  ├─ 业务对象
│  ├─ 用户角色
│  ├─ 前置条件
│  ├─ 主流程
│  ├─ 业务规则
│  ├─ 限制条件
│  ├─ 已定义异常处理
│  └─ 未确认事项
├─ Risk Context
│  ├─ 风险关注点
│  ├─ 历史问题
│  ├─ 已知事故模式
│  ├─ 高风险边界
│  └─ 风险适用范围
└─ Validation Context
   ├─ 验证关注点
   ├─ 历史测试经验
   ├─ 回归范围
   ├─ 常见遗漏用例
   └─ 验收注意事项
```

### 字段归属

| 字段 | 推荐 Context | 主要维护者 | 主要消费者 |
|---|---|---|---|
| 功能目标 | Business Context | 产品 | Agent1A、Agent4 |
| 业务对象 | Business Context | 产品，测试补充 | Agent1A、Agent2 |
| 用户角色 | Business Context | 产品 | Agent1A、Agent2 |
| 前置条件 | Business Context | 产品，测试补充 | Agent1A、Agent3 |
| 主流程 | Business Context | 产品 | Agent1A、Agent3 |
| 业务规则 | Business Context | 产品 | Agent1A、Agent2、Agent3 |
| 限制条件 | Business Context | 产品，测试补充 | Agent1A、Agent2、Agent3 |
| 异常场景 | Business Context / Risk Context | 测试，产品确认 | Agent2、Agent3 |
| 风险关注点 | Risk Context | 测试 | Agent2 |
| 历史问题 | Risk Context | 测试，研发补充 | Agent2、Agent4 |
| 验证关注点 | Validation Context | 测试 | Agent3 |
| 未确认事项 | Business Context | 产品，测试补充 | Agent1A、Agent2、Agent4；Agent1B 仅通过 Agent1A Artifact 间接消费 |

拆分后仍可由 Context Compiler 编译为当前 Runtime Context Package V2；拆分只发生在人工维护层，不要求当前系统增加 Agent 或新的下游流程。

## 三、真实维护场景模拟

### 案例 1：新增功能需求

场景：新增“手机号一键登录”。

人工需要修改：

- 在 Business Context 新增功能目标。
- 新增业务对象：手机号、验证码、登录态。
- 新增用户角色：未登录用户、已有账号用户。
- 编写主流程：输入手机号 -> 获取验证码 -> 验证 -> 登录成功。
- 明确业务规则：手机号必须已注册、验证码校验必需。
- 写出限制条件：未注册手机号不能直接登录。
- 列出未确认事项：验证码有效期、发送频率、失败处理、是否记录登录失败日志。

系统应该自动完成：

- 生成稳定 id。
- 根据模块和章节生成 source_ref。
- 把业务规则编译为 Runtime `business_rules`。
- 把限制条件编译为 Runtime `constraints`。
- 把未确认事项编译为 Runtime `unknowns`。
- 保留版本、owner、effective_date。
- 生成 Agent Context View。

人工不应该做：

- 手写 `confirmed_facts` / `business_rules` / `constraints` JSON。
- 手动维护 item id。
- 手动拼 Agent 输入。

### 案例 2：已有功能规则变更

场景：个人资料中手机号原来不可修改，现在允许修改，但需要二次验证和人工审核。

人工需要修改：

- 在 Business Context 中更新对应模块版本。
- 修改状态：旧版本标记为 `deprecated`，新版本标记为 `active`。
- 修改限制条件：从“手机号不可修改”变为“手机号不可直接修改”。
- 新增业务规则：修改手机号需要二次验证和人工审核。
- 更新主流程：提交修改申请 -> 二次验证 -> 审核 -> 生效。
- 增加未确认事项：审核时限、审核失败处理、旧手机号通知规则。
- 记录 change_reason。

系统应该自动完成：

- 阻止 deprecated 规则进入 Runtime。
- 检测同一模块中 active 规则冲突。
- 将新规则编译到 Runtime Context Package V2。
- 将旧规则保留为历史记录，但不进入 Agent Context View。
- 在输出中保留 source_ref 和版本信息。

人工不应该做：

- 在多个 JSON section 中手动删除旧规则。
- 手动判断哪些 item 要分发给哪个 Agent。
- 手动修复旧规则污染。

### 案例 3：历史 Bug 和测试经验补充

场景：历史 Bug 显示“注册成功后状态误判为已登录”，历史测试经验提示“需要验证注册后登录态和跳转页面”。

人工需要修改：

- 在 Risk Context 中新增历史问题：
  - 问题描述。
  - 影响模块。
  - 触发条件。
  - 当前是否仍适用。
  - 风险级别。
- 在 Validation Context 中新增验证关注点：
  - 注册成功后不应自动登录。
  - 注册成功后应进入登录流程。
  - 登录态、跳转页、日志记录需要回归。

系统应该自动完成：

- 保留历史 Bug 来源。
- 将历史问题标记为风险经验，而不是业务规则。
- 将验证关注点提供给 Agent3，而不是污染 Agent1A 的需求事实。
- 在 Trace 中记录 Agent2/Agent3 是否消费了这些经验。

人工不应该做：

- 把历史 Bug 改写成业务规则。
- 把测试用例复制成 Runtime JSON。
- 手动判断 Agent1A/2/3 分别看哪些内容。

## 四、维护成本分析

假设企业有：

- 100 个功能模块。
- 500 条业务规则。
- 1000 条历史 Bug。

### 人工维护成本在哪里

| 成本项 | 主要承担者 | 成本来源 | 是否可自动化 |
|---|---|---|---|
| 判断规则是否当前有效 | 产品 | 需要业务决策 | 不可完全自动化 |
| 判断规则适用范围 | 产品，测试 | 需要理解业务边界 | 不可完全自动化 |
| 解决规则冲突 | 产品，研发，测试 | 需要确认真实线上行为和目标版本 | 不可完全自动化 |
| 给规则写版本和 owner | 产品 | 管理成本 | 可用模板降低，但需人工确认 |
| 把文档整理成 JSON | 产品/测试 | 格式劳动 | 应自动化 |
| 生成 item id | 系统 | 机械工作 | 可自动化 |
| 生成 source_ref | 系统 | 机械工作 | 可自动化 |
| 从历史 Bug 中提取候选风险 | 系统辅助，测试审核 | 初筛可自动，适用性需确认 | 半自动 |
| 维护验证关注点 | 测试 | 需要测试经验 | 可由历史测试资产辅助，但需人工确认 |
| 判断 historical item 是否仍适用 | 产品/测试 | 需要上下文判断 | 不可完全自动化 |

### 规模化后的主要风险

1. 如果仍让人工维护 Runtime JSON，500 条规则会迅速变成格式维护负担。
2. 如果不拆 Business/Risk/Validation，1000 条历史 Bug 容易污染业务事实。
3. 如果没有版本状态，旧规则会持续影响新需求分析。
4. 如果没有模块归属，规则复用会变成全文检索式误召回。
5. 如果没有 owner，冲突规则无法快速确认。

### 哪些可以自动化

- 模板生成。
- section 解析。
- item id 生成。
- source_ref 生成。
- 版本状态检查。
- active/deprecated 过滤。
- 冲突候选提示。
- 从 Bug/测试资产生成候选 Risk/Validation item。
- 编译 Runtime Context Package V2。
- 生成 Agent Context View。

### 哪些必须人工承担

- 业务规则确认。
- 当前有效版本确认。
- 冲突解决。
- 适用范围判断。
- 风险优先级判断。
- 历史 Bug 是否仍适用。
- 验证关注点是否对当前模块有价值。

结论：规模化后最大的人工成本不应是“整理格式”，而应是“做业务判断”。Human Context Model V1 必须把这两类工作分开。

## 五、推荐 Human Context Model V1

### 总体形态

推荐 V1 采用“三类上下文 + 模块化维护”的人工模型：

```text
Human Context Model V1
├─ Business Context
├─ Risk Context
└─ Validation Context
```

三类 Context 都围绕同一个 `module_id` 关联，不要求业务人员理解 Runtime V2 section。

### 1. Business Context V1

适合产品人员主维护，测试人员补充边界。

```yaml
context_type: business
module_id: account_registration
module_name: 账号注册
version: v2.1
status: active
effective_date: 2026-08-01
owner: account-product-team
change_reason: 明确手机号注册和验证码规则
```

建议字段：

```markdown
## 功能目标

## 业务对象

## 用户角色

## 前置条件

## 主流程

## 业务规则

## 限制条件

## 已定义异常处理

## 未确认事项
```

维护要求：

- 必填：功能目标、业务对象、用户角色、主流程、业务规则、限制条件、未确认事项。
- 建议：前置条件、已定义异常处理。
- 不放：历史 Bug、测试用例、纯测试经验。

业务价值：

- 降低人工需求分析成本：是，模块规则可以复用。
- 提高风险识别质量：是，Agent2 有稳定规则和 unknown。
- 提升历史经验复用效率：是，历史需求规则沉淀为当前有效上下文。

### 2. Risk Context V1

适合测试人员主维护，产品/研发确认适用性。

```yaml
context_type: risk
module_id: account_registration
version: risk-v1
status: active
owner: qa-team
source_system: bug_tracker
```

建议字段：

```markdown
## 风险关注点

## 历史问题

## 触发条件

## 影响范围

## 当前是否仍适用

## 风险优先级

## 关联业务规则
```

维护要求：

- 必填：历史问题、影响范围、当前是否仍适用、风险优先级。
- 建议：触发条件、关联业务规则。
- 不放：业务规则原文、测试用例步骤。

业务价值：

- 降低人工需求分析成本：是，减少测试人员翻历史 Bug。
- 提高风险识别质量：是，这是 Agent2 最直接的高价值输入。
- 提升历史经验复用效率：是，把 Bug 经验从一次性记录变成风险模式。

### 3. Validation Context V1

适合测试人员维护。

```yaml
context_type: validation
module_id: account_registration
version: validation-v1
status: active
owner: qa-team
source_system: test_asset
```

建议字段：

```markdown
## 验证关注点

## 回归范围

## 历史遗漏点

## 常见异常输入

## 验收注意事项

## 不适用范围
```

维护要求：

- 必填：验证关注点、回归范围。
- 建议：历史遗漏点、常见异常输入、验收注意事项。
- 不放：业务规则确认、产品决策。

业务价值：

- 降低人工需求分析成本：是，减少每次重新想测试关注点。
- 提高风险识别质量：间接，通过覆盖历史遗漏点。
- 提升历史经验复用效率：是，复用历史测试资产。

## 六、推荐维护流程

### 新增功能

```text
产品维护 Business Context
测试补充 Risk/Validation 候选
人工确认有效性
系统编译 Runtime Context Package V2
进入现有 Workflow
```

### 规则变更

```text
产品更新 Business Context version/status
系统阻止旧版本进入 Runtime
测试检查 Risk/Validation 是否需要更新
系统重新编译 Runtime Context Package V2
```

### Bug/测试经验补充

```text
测试维护 Risk Context 或 Validation Context
产品/研发确认是否仍适用
系统只把适用内容提供给对应 Agent
不污染 Business Context
```

## 七、最终结论

### 1. 当前 Human Context Model 字段是否合理

字段集合整体合理，但需要拆分职责。

- 功能目标、业务对象、用户角色、前置条件、主流程、业务规则、限制条件、未确认事项属于 Business Context。
- 风险关注点、历史问题属于 Risk Context。
- 验证关注点属于 Validation Context。
- 异常场景需要分流：已定义处理规则进入 Business Context；历史高风险异常进入 Risk Context；测试输入覆盖进入 Validation Context。

### 2. 是否应该拆成三类 Context

应该拆。

拆分不是为了技术复杂度，而是为了贴近真实维护方式：

- 产品维护业务事实和规则。
- 测试维护风险和验证经验。
- 系统负责统一编译和分发。

### 3. 推荐 Human Context Model V1

推荐 V1 为：

```text
Business Context V1
Risk Context V1
Validation Context V1
```

三类 Context 使用相同的模块标识、版本状态、owner 和来源字段关联，维护内容按业务职责拆分。

### 4. 是否能降低需求分析成本

能，但前提是不要让人工手写 Runtime JSON。

它降低的是：

- 重复翻历史需求的成本。
- 重复整理业务规则的成本。
- 每次重新回忆历史 Bug 和测试经验的成本。

它不会消除：

- 业务规则确认。
- 冲突解决。
- 当前适用性判断。

### 5. 是否能支持 Agent 风险分析

能，尤其是拆出 Risk Context 后。

当前仅 Business Context 能支持规则缺口类风险。Risk Context 能进一步支持：

- 历史缺陷复现风险。
- 高频遗漏风险。
- 版本变更风险。
- 异常流程风险。

### 6. 是否应继续保持轻量

应保持轻量。

当前不要做：

- RAG。
- 知识库。
- Agent 平台。
- 自动文档理解。
- 全量企业知识治理。

下一步最小验证应是：选一个账号模块，用同一份业务内容分别维护 Business/Risk/Validation 三类人工上下文，检查产品和测试是否能独立维护，并验证编译后的 Runtime Context 是否足够支撑现有五 Agent。
