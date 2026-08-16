# Execution Trace Phase 1

Execution Trace 只记录运行过程，不参与调度、校验、重试或路由，也不改变 Agent 输入输出。

## 1. Trace 文件

当前保留三个 JSONL 文件：

```text
outputs/traces/{run_id}/workflow_events.jsonl
outputs/traces/{run_id}/agent_traces.jsonl
outputs/traces/{run_id}/tool_traces.jsonl
```

用途：

| 文件 | 用途 |
|---|---|
| `workflow_events.jsonl` | 统一事件流，按写入顺序还原 Tool、Skill 和 Agent 的实际调用链 |
| `agent_traces.jsonl` | Agent 调用兼容视图 |
| `tool_traces.jsonl` | Tool/Skill Context 调用兼容视图 |

后续排查一次 run 的完整执行顺序，优先看 `workflow_events.jsonl`。

## 2. 统一事件结构

```json
{
  "event_id": "string",
  "event_type": "tool|skill|agent",
  "capability_type": "tool|skill|agent",
  "run_id": "string",
  "case_id": "string",
  "name": "string",
  "stage": "string|null",
  "input_refs": ["string"],
  "output_ref": "string|null",
  "output_snapshot": {},
  "execution_status": "completed|failed",
  "human_review": {},
  "error": {},
  "recorded_at": "string",
  "payload": {}
}
```

`payload` 保留原始 Agent Trace 或 Context capability Trace，避免为了统一事件流丢失细节。

## 3. Agent Trace

每个 Agent 执行后追加一条记录：

```json
{
  "trace_id": "string",
  "run_id": "string",
  "case_id": "string",
  "agent_id": "string",
  "stage": "string",
  "registry_ref": {
    "registry_version": "v2",
    "agent_id": "string",
    "stage": "string",
    "schema_name": "string",
    "prompt_ref": "string",
    "implementation_ref": "string"
  },
  "input_sources": ["string"],
  "output_snapshot": {},
  "execution_status": "completed",
  "human_review": {
    "required": false,
    "reasons": []
  },
  "recorded_at": "string"
}
```

## 4. Context Capability Trace

Markdown Tool 示例：

```json
{
  "tool_id": "local_markdown_context_reader",
  "capability_type": "tool",
  "input_refs": ["context_sources[0]"],
  "output_ref": "workflow_state.context.items.product_context",
  "execution_status": "completed|failed"
}
```

Repository Skill 示例：

```json
{
  "tool_id": "understand_domain_repository_context",
  "capability_type": "skill",
  "input_refs": ["context_sources[0]"],
  "output_ref": "workflow_state.context.items.repo_context",
  "output_snapshot": {
    "context_id": "repo_context",
    "provider_id": "understand_domain_repository_context_provider",
    "skill_id": "understand_domain_repository_context",
    "capability_type": "skill",
    "required": false,
    "status": "success|failed"
  },
  "execution_status": "completed|failed"
}
```

本阶段不新增 `skill_traces.jsonl`，避免为不同能力继续扩展独立 Trace 体系。

## 5. External Skill 边界

当前只接入一个受限本地 Repository Context Skill：

```text
understand_domain_repository_context
```

边界：

- 不远程访问 GitHub。
- 不联网。
- 不执行 shell 命令。
- 不触发 Skill CLI 的默认写入。
- 不触发子 Agent。
- 不让 Agent 自主选择 Skill。
- Registry 仍只声明，不参与调度。

## 6. 当前不做

- 不创建通用 Skill 平台。
- 不引入动态路由。
- 不增加 Agent 数量。
- 不修改 Pipeline 顺序。
- 不修改 Agent Prompt、职责或业务 Schema。
- 不同时接入多个 Skill。
- Trace 写入失败只能打印警告，不得改变主流程结果。
