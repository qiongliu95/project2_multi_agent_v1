# Harness Design

## Purpose

为了验证 Multi-Agent 工作流是否真正带来收益，本项目设计了一个最小实验框架（Harness）。

Harness 不参与业务逻辑生成。

其职责是：

* 统一执行 Pipeline
* 管理测试 Case
* 保存运行结果
* 支持不同方案对比

核心目标：

> 为 Agent 实验提供可重复验证环境。

---

## Why Harness

在项目早期实验中发现：

仅观察单次运行结果，无法判断：

* 问题来自 Prompt 还是 Agent 结构
* 优化是否真正有效
* 不同方案之间是否存在稳定差异

因此需要建立统一实验框架。

用于：

* 固定输入
* 固定输出结构
* 固定实验流程

保证不同方案能够在相同条件下进行比较。

---

## Architecture

Harness 位于 Agent Pipeline 外层。

整体结构如下：

Test Cases

↓

Harness

↓

Pipeline

↓

Outputs

Harness 负责：

1. 加载测试案例
2. 调用 Pipeline
3. 保存运行结果
4. 组织实验数据

Pipeline 负责：

1. 需求解析
2. 风险识别
3. 测试设计
4. 结果汇总

职责完全分离。

---

## Current Capabilities

当前版本支持：

### Case Management

统一管理测试案例：

* CRUD 类需求
* 流程类需求
* AI 能力类需求
* 工具类需求
* 平台能力类需求

---

### Pipeline Execution

统一执行：

Requirement Parsing

↓

Risk Analysis

↓

Test Design

↓

Result Summary

保证不同实验使用相同运行链路。

---

### Result Recording

自动保存：

* 输入需求
* 各 Agent 输出
* 最终结果

用于后续分析与对比。

---

## Comparison Support

Harness 支持：

同一测试案例运行不同方案。

例如：

### Baseline

Requirement

↓

Agent Pipeline

---

### Three-Stage Agent1

Requirement

↓

Parsing

↓

Gap Detection

↓

Selection

↓

Agent Pipeline

通过统一输入与输出结构进行比较。

---

## Design Principles

### Principle 1

实验框架与业务逻辑解耦。

Harness 不参与生成。

只负责运行与记录。

---

### Principle 2

Baseline 始终保持可运行。

扩展方案默认独立存在。

避免实验影响主链路稳定性。

---

### Principle 3

所有优化必须通过对比验证。

不依赖主观观察判断效果。

---

## Current Limitations

当前 Harness 仅用于实验验证。

不包含：

* 自动评测系统
* 动态路由
* 多轮对话
* UI 展示
* 复杂编排能力

目标是保持最小可验证结构。

---

## Conclusion

Harness 并非项目核心能力。

其价值在于：

为 Agent 实验提供统一验证环境。

通过固定输入、固定流程和结果归档，

支持：

* Prompt 收敛验证
* Agent 结构对比
* 方案效果分析

从而让实验结论具备可重复性与可追溯性。
