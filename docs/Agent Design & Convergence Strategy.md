# Agent Design

## Project Goal

本项目构建了一套从需求分析到测试设计的 Multi-Agent Workflow。

目标不是生成更多内容，而是验证：

> 通过任务拆分与边界约束，是否能够提升输出的可控性与稳定性。

---

## Design Principles

在实验过程中发现：

单一 Agent 直接完成：

需求分析
→ 风险识别
→ 测试设计
→ 汇总输出

容易出现：

* 常识补全
* 风险泛化
* 伪完整结果
* 汇总扩写

因此采用职责拆分方案。

核心原则：

### Principle 1

单 Agent 只负责单一认知任务。

避免同时承担：

* 信息提取
* 风险判断
* 测试设计

等不同任务。

---

### Principle 2

每个 Agent 输出结构化结果。

便于：

* 下游消费
* 结果追溯
* 问题定位

---

### Principle 3

允许停止生成。

当信息不足时：

输出问题而不是补全答案。

---

## Overall Architecture

Requirement Text

↓

Agent 1：Requirement Parsing

↓

Agent 2：Risk Analysis

↓

Agent 3：Test Design

↓

Agent 4：Result Summary

---

## Agent 1：Requirement Parsing

### Responsibility

将原始需求转化为结构化需求信息。

输出：

* functional_goal
* user_roles
* main_flow
* preconditions
* edge_cases
* open_questions

---

### Convergence Problem

早期版本存在：

* 常识补全
* 隐式需求推断
* 问题泛化

例如：

需求中未出现验证码，

仍自动生成验证码流程。

---

### Convergence Strategy

限制信息来源：

仅允许基于原始需求文本提取。

缺失信息统一进入：

open_questions

---

### Final Role

负责：

提取信息

不负责：

补全信息

---

## Agent 2：Risk Analysis

### Responsibility

识别需求中的风险与缺失信息。

输出：

* ambiguity_risks
* missing_information
* edge_case_risks
* data_risks
* performance_risks

---

### Convergence Problem

早期版本容易生成：

通用风险 Checklist

例如：

* 安全风险
* 权限风险
* 性能风险

即使需求中没有相关信息。

---

### Convergence Strategy

限制风险来源：

仅允许引用：

* requirement_text
* Agent1 输出
* open_questions

---

### Final Role

负责：

显式暴露需求风险。

不负责：

补充新的业务规则。

---

## Agent 3：Test Design

### Responsibility

根据需求与风险生成测试设计结果。

输出：

* core_test_points
* edge_test_points
* performance_test_points
* acceptance_criteria
* test_case_drafts

---

### Convergence Problem

早期版本倾向生成：

伪完整测试用例。

即使需求信息不足：

仍会补全大量细节。

---

### Convergence Strategy

引入：

test_case_drafts

规则：

信息不足时：

停止生成完整测试用例。

---

### Final Role

负责：

测试设计。

不负责：

补全需求。

---

## Agent 4：Result Summary

### Responsibility

整合前序 Agent 输出。

输出：

* requirement_summary
* risk_summary
* testing_recommendations
* critical_open_questions

---

### Convergence Problem

汇总阶段容易出现扩写。

新增：

* 风险
* 问题
* 建议

导致结果失真。

---

### Convergence Strategy

仅允许复用：

* Agent1 输出
* Agent2 输出
* Agent3 输出

禁止新增内容。

---

### Final Role

负责：

信息整合。

不负责：

继续推理。

---

## Agent1 Three-Stage Extension

在实验过程中发现：

单阶段 Parsing 在复杂需求下存在稳定性问题。

因此引入：

Parsing

↓

Gap Detection

↓

Selection

新增中间状态：

action_gap_candidates

作用：

* 显式识别信息缺口
* 提升问题覆盖率
* 提升可解释性

实验结果表明：

Three-Stage 方案在复杂需求场景下优于 Baseline。

---

## Key Findings

实验过程中发现：

### Finding 1

多 Agent 并不会天然提升质量。

---

### Finding 2

系统稳定性主要来自：

* 职责边界
* 信息来源约束
* 输出结构约束

---

### Finding 3

模型天然倾向补全缺失信息。

需要显式限制。

---

### Finding 4

系统应支持：

信息不足 → 停止生成

而不是：

信息不足 → 自动补全

---

## Final Conclusion

本项目最终验证：

对于需求分析与测试设计场景，

Multi-Agent 的价值不在于增加 Agent 数量，

而在于：

* 任务拆分
* 生成约束
* 边界控制
* 信息缺口显式化

系统稳定性来自约束设计，而非模型能力本身。
