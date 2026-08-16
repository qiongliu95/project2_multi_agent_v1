# Compare Log

## Purpose

本实验用于验证：

> Agent1 引入中间状态（Gap Detection）后，是否能够提升需求缺口识别的稳定性与一致性。

对比对象：

* Baseline Agent1
* Three-Stage Agent1

---

## Compared Architectures

### Baseline

Requirement Text

↓

Requirement Parsing

↓

Open Questions

特点：

* 单阶段生成
* 直接从需求提取并生成问题
* 结构简单

---

### Three-Stage

Requirement Text

↓

Parsing

↓

Gap Detection

↓

Selection

↓

Open Questions

新增中间状态：

* action_gap_candidates

特点：

* 显式识别信息缺口
* 问题生成与问题筛选解耦
* 支持中间结果观察

---

## Evaluation Focus

本次实验重点关注：

1. 是否能够识别需求缺口
2. 是否遗漏关键动作
3. 是否出现无依据补全
4. Open Questions 是否稳定

---

## Representative Cases

### Case 1：CRUD Requirement

输入：

用户可以创建和删除自己的笔记。

观察：

* Baseline 能识别主要动作
* Three-Stage 同样完成识别

结果：

两者表现接近。

结论：

简单需求下，Three-Stage 优势不明显。

---

### Case 2：Review Workflow

输入：

管理员可以审核用户提交的内容，审核通过后内容对外展示。

观察：

* Baseline 存在问题覆盖波动
* Three-Stage 对审核流程缺口识别更稳定

结果：

Three-Stage 输出一致性更高。

---

### Case 3：AI Capability Requirement

输入：

系统可以对用户输入的文本生成摘要。

观察：

* Baseline 容易引入推测性问题
* Three-Stage 更倾向于识别真实缺失信息

结果：

Three-Stage 扩写减少。

---

### Case 4：Multi-Action Requirement

输入：

用户可以上传图片并进行识别。

观察：

* Baseline 在部分运行中存在动作覆盖不完整
* Three-Stage 能稳定覆盖上传与识别两个动作

结果：

Three-Stage 对多动作需求更稳定。

---

## Key Findings

### Finding 1

复杂需求中的问题并不来自 Question Generation。

而是来自：

需求缺口识别不稳定。

---

### Finding 2

Gap Detection 与 Selection 分离后：

问题来源更加可解释。

---

### Finding 3

中间状态能够提升系统可观测性。

开发者可以明确看到：

* 哪些动作被识别
* 哪些动作存在缺口
* 哪些问题最终被保留

---

## Final Conclusion

实验结果表明：

Three-Stage Agent1 在复杂需求场景下优于 Baseline。

主要收益并非来自更多 Prompt，而是来自：

* 中间状态设计
* 任务解耦
* 显式缺口识别

结论：

对于需求分析任务，

Parsing → Gap Detection → Selection

比单阶段 Parsing → Questions 更稳定、更可解释。
