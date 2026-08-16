# Multi-Agent 需求分析系统

> 项目状态：已完成 Project Exit，当前版本冻结。
>
> 本项目是面向作品集和面试展示的轻量 AI Workflow，不是生产级 Agent 平台、RAG 平台、企业知识库或自动测试平台。

## 1. 项目解决什么问题

本项目验证一个核心问题：

> 当输入当前需求文本和可选历史上下文时，如何通过固定五 Agent Workflow、Context View、Stage Artifact 和 Trace，让 AI 辅助产品/测试人员完成需求理解、缺口识别、风险分析和验证关注点生成，同时避免信息不足时的伪完整输出。

当前最终定位：

- 辅助需求理解和拆解。
- 显式保留 unknown，而不是把未知信息补成事实。
- 利用 Structured Context 让已有规则、限制、流程进入分析链路。
- 通过 Stage Artifact 控制 Agent 间信息传递。
- 通过 Trace 支持人工复核。
- 通过 Evaluation MVP 给出停止标准和项目结项判断。

不解决：

- 不建设完整企业知识库。
- 不建设 RAG / 知识图谱。
- 不做自动测试平台。
- 不做动态 Agent 调度平台。
- 不保证生产级稳定性或多模型 Benchmark。

## 2. 当前最终 Workflow

```text
Context Source
  -> Context Package / Context View
  -> Agent1A 需求解析与缺口识别
  -> Agent1B 澄清问题生成
  -> Agent2 风险分析
  -> Agent3 验证关注点生成
  -> Agent4 汇总与人工复核判断
  -> Final Output + Trace
```

五个 Agent 的当前职责：

| Agent | 当前阶段 | 职责 |
|---|---|---|
| Agent1A | requirement_gap_detection | 需求结构提取、主流程识别、known_conditions / specific_unknowns / context_refs 生成 |
| Agent1B | clarification | 只基于 Agent1A Stage Artifact 生成澄清问题，不直接消费完整 Context |
| Agent2 | risk_analysis | 基于需求、Agent1A/1B Artifact 和 Context View 识别风险，并输出 `risk_items` |
| Agent3 | controlled_test_draft | 基于风险、规则、限制和 unknown 生成验证关注点，不把 unknown 当确定事实 |
| Agent4 | review | 汇总 Stage Artifact，判断是否需要人工复核，不重新分析原始 Context |

## 3. 当前支持的输入路径

### 3.1 Text Only

只输入当前需求文本。用于验证基础 Workflow 是否成立。

```bash
python verify_workflow.py --mode text --agent-mode fake
python verify_workflow.py --mode text --agent-mode real
```

### 3.2 Markdown Context

读取本地 Markdown 上下文，作为低门槛原始资料路径。该路径主要用于观察原始上下文进入 Workflow 的效果。

```bash
python verify_workflow.py --mode markdown --agent-mode fake
```

### 3.3 Structured Context V2

读取 Context Package V2 JSON，并转换为 Agent Context View。

```bash
python verify_workflow.py --mode structured --structured-context data/context/registration_context_v2.json --agent-mode fake
```

### 3.4 Human Context Compiler

将人工维护的业务 Markdown 编译为 Context Package V2，再走 Structured Context Runtime。

```bash
python compile_context.py --input data/human_context/evaluation/case_01_email_binding.md
python verify_workflow.py --mode structured --structured-context outputs/compiled_context/{context_id}.json --agent-mode fake
```

### 3.5 Auto Context

自动上下文准备实验路径：历史文档索引 -> 候选召回 -> review queue -> approved consumable context。该路径只作为实验材料保留，不作为当前结项后的继续扩展方向。

```bash
python prepare_context.py index --source-dir data/history
python prepare_context.py prepare --requirement-text "..."
python prepare_context.py build --queue outputs/context_review_queue/{run_id}.json
python verify_workflow.py --mode auto-context --consumable-context outputs/consumable_context/{run_id}.json --agent-mode fake
```

## 4. 面向真实使用者的入口

真实使用入口是单文件需求投放：

```bash
python run_requirement_inbox.py
```

默认读取：

```text
data/requirements_inbox/*.md
```

常用命令：

```bash
python run_requirement_inbox.py --input-dir data/requirements_inbox --agent-mode real
python run_requirement_inbox.py --file data/requirements_inbox/example.md --agent-mode fake
```

输出目录：

```text
outputs/requirement_runs/{run_id}/
```

详见：`docs/requirement_inbox.md`。

## 5. 关键目录说明

| 路径 | 用途 |
|---|---|
| `core/` | 当前运行核心代码：Agent wrapper、Pipeline、Context Tools、Trace、Compiler、LLM Client |
| `prompts/` | 五个 Agent 的 Prompt |
| `configs/` | Pipeline config 和声明式 Agent Registry；Registry 只用于 Trace/架构说明，不参与调度 |
| `data/evaluation_cases/` | 三个最终 evaluation case |
| `data/context/` | Structured Context V2 样例与 evaluation context |
| `data/human_context/` | Human Context Compiler 输入样例 |
| `data/history/` | Auto Context 实验用历史资料 |
| `data/requirements_inbox/` | 真实使用入口的需求投放目录 |
| `outputs/context_comparison_p1_real/` | 最终 A/B/C Context Path 对比运行证据 |
| `outputs/evaluation_runs/` | Text Only 核心 evaluation run 证据 |
| `outputs/human_eval_review_pack/` | Human Semantic Evaluation 审阅包 |
| `outputs/verify_runs/`, `outputs/traces/` | verify_workflow 产生的观测结果和 Trace |
| `docs/project_exit_report.md` | 最终项目结项报告，当前最高优先级结论文档 |

## 6. 评估与结项结论

最终评估不使用唯一 Golden Answer，而使用 Human Semantic Evaluation、must_cover / valid_optional / unsupported、Minimal System Readiness 和 Context Path 对比证据。

最终结论见：

- `docs/project_exit_report.md`
- `docs/evaluation_mvp_final.md`
- `docs/human_evaluation_scorecards/`
- `outputs/human_eval_review_pack/`

当前 Project Exit 最终结论：

```text
exit_approved
```

核心验证结论：

- Text Only baseline 已达到 acceptable、evaluable、usable as comparison baseline。
- Structured Context 存在稳定正向价值，重点是提高 known / unknown / risk 边界稳定性。
- Human Context Compiler 路径基本可接受，未发现稳定的关键规则丢失、真实 unknown 消失或核心流程误解。
- Agent2 risk amplification 和 Agent3 all-or-nothing 属于 Non-blocking semantic issue / Known Limitation。

## 7. 推荐复现命令

基础结构观察：

```bash
python verify_workflow.py --mode text --agent-mode fake
python verify_workflow.py --mode structured --agent-mode fake
```

真实需求投放：

```bash
python run_requirement_inbox.py --agent-mode fake
```

最终 Context A/B/C 对比复现：

```bash
python evaluate_context_comparison.py --agent-mode fake --output-root outputs/context_comparison_runs/demo_fake
```

如果使用真实模型，需要 `.env` 中配置 OpenAI-compatible API：

```text
LLM_API_KEY=...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

## 8. 已知限制

- 当前不是生产系统，真实模型运行仍可能受 API / 网络波动影响。
- Agent2 可能出现 risk amplification。
- Agent3 对局部 unknown 的处理有时偏保守，可能 all-or-nothing。
- Human Context Compiler 已验证运行链路和基本信息保真，不代表已验证长期人工维护成本下降。
- Auto Context 是实验路径，不作为当前冻结版本的主线扩展方向。
- 历史设计文档和早期实验输出作为演进证据保留，最终口径以 `docs/project_exit_report.md` 和本 README 为准。

## 9. 当前冻结原则

当前版本已经完成 Project Exit。除非重新立项，否则不继续：

- 新增 Agent。
- 扩展 RAG / 知识库 / 知识图谱。
- 扩展 Auto Context。
- 针对单次模型输出继续修改 Prompt。
- 建设完整 Evaluation 平台。
