# Technical Solution

## 1. Design Objective

本项目并非构建完整 Agent 平台。

项目目标是验证：

> 在需求分析与测试设计场景中，多 Agent 拆分是否能够提升输出的可控性、稳定性与可复核性。

因此技术方案优先考虑：

* 可验证
* 可解释
* 可复现
* 可对比

而不是：

* 产品化能力
* 工程复杂度
* 多模型编排
* 工具生态集成

---

## 2. Overall Architecture

系统采用串行 Multi-Agent Workflow：

Requirement Text

↓

Agent 1：Requirement Parsing

↓

Agent 2：Risk Analysis

↓

Agent 3：Test Design

↓

Agent 4：Result Summary

↓

Structured Output

---

## 3. Core Design Decisions

### Decision 1：Single Model

项目采用单模型方案。

原因：

* 降低实验变量
* 聚焦验证 Agent 拆分价值
* 避免模型能力差异影响实验结果

如果同时引入：

* 多模型协同
* 模型自动路由
* 模型能力分配

则无法判断：

实验效果究竟来自 Agent 设计还是模型差异。

因此当前统一采用单模型运行。

---

### Decision 2：Sequential Workflow

项目采用串行工作流。

原因：

需求分析与测试设计天然存在依赖关系：

Requirement Parsing

↓

Risk Analysis

↓

Test Design

↓

Summary

后续阶段需要消费前序阶段结果。

因此采用：

Sequential Workflow

而非：

* Parallel Agent
* Dynamic Routing
* Graph Workflow

---

### Decision 3：Structured Output

所有 Agent 输出固定 Schema。

原因：

自由文本容易出现：

* 输出漂移
* 字段缺失
* 信息混杂

因此统一采用结构化输出。

示例：

Agent 1

* functional_goal
* user_roles
* main_flow
* open_questions

Agent 2

* ambiguity_risks
* missing_information
* edge_case_risks

Agent 3

* core_test_points
* acceptance_criteria
* test_case_drafts

Agent 4

* requirement_summary
* risk_summary
* testing_recommendations

---

### Decision 4：Human Review Point

系统保留人工复核节点。

实验过程中发现：

即使经过 Agent 拆分与约束设计，

模型仍可能：

* 误解需求
* 错误推断
* 扩展业务规则

因此系统输出定位为：

辅助分析结果

而非：

最终决策结果

人工复核仍然保留在流程末端。

---

## 4. Constraint Strategy

项目核心技术策略并非增加 Agent 数量。

而是增加约束。

---

### Agent 1

限制信息来源。

仅允许基于：

requirement_text

进行信息提取。

缺失信息统一进入：

open_questions

---

### Agent 2

限制风险来源。

风险仅允许基于：

* requirement_text
* Agent 1 输出

进行识别。

禁止引入新的业务规则。

---

### Agent 3

引入停止生成机制。

信息不足时：

输出：

test_case_drafts

而非：

完整测试用例。

---

### Agent 4

限制汇总范围。

禁止：

* 新增问题
* 新增风险
* 新增建议

仅允许整合已有结果。

---

## 5. Experimental Infrastructure

为了验证不同方案效果，

项目引入最小 Harness。

职责包括：

* 管理测试案例
* 执行 Pipeline
* 保存运行结果
* 支持方案对比

典型实验：

Baseline

vs

Three-Stage Agent1

用于验证：

中间状态设计是否提升输出稳定性。

---

## 6. Alternative Solutions Considered

实验过程中评估过以下方案：

### Multi-Model Architecture

未采用。

原因：

增加变量过多。

无法聚焦验证 Agent 拆分价值。

---

### Dynamic Routing

未采用。

原因：

当前任务链路固定。

路由不会直接提升实验价值。

---

### Tool Calling

未采用。

原因：

当前重点在：

生成控制

而非：

工具协作能力。

---

## 7. Current Scope

当前验证内容：

* Multi-Agent 拆分
* Prompt 约束
* 输出结构控制
* 信息缺口识别
* 停止生成机制

当前不验证：

* 多模型协同
* 动态路由
* Tool Calling
* 长期记忆
* 产品化系统

---

## 8. Key Findings

实验结果表明：

系统稳定性并不来自更多 Agent。

而来自：

* 职责边界
* 信息来源限制
* 输出结构约束
* 中间状态设计
* 停止生成机制

其中：

约束设计对结果质量的影响，

明显大于 Agent 数量本身。

---

## 9. Conclusion

本项目采用：

Single Model

*

Sequential Workflow

*

Structured Output

的最小技术方案。

目标不是构建复杂系统，

而是验证：

在需求分析与测试设计场景下，

通过任务拆分与边界约束，

是否能够实现更稳定、更可控的生成过程。

实验结果证明：

系统稳定性主要来自约束设计，而非模型能力本身。
