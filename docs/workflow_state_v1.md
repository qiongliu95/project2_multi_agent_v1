# Workflow State V1

Workflow State 记录一次固定五 Agent Pipeline 的外层运行状态。

它不替代 Agent 业务输出，不改变 Agent Prompt、Schema、职责或执行顺序。

## 1. 当前结构

```json
{
  "run_id": "",
  "input": {
    "requirement_text": "",
    "context_sources": []
  },
  "context": {
    "items": []
  },
  "stages": {
    "agent1a": {
      "status": "pending",
      "output": null,
      "error": null
    },
    "agent1b": {
      "status": "pending",
      "output": null,
      "error": null
    },
    "agent2": {
      "status": "pending",
      "output": null,
      "error": null
    },
    "agent3": {
      "status": "pending",
      "output": null,
      "error": null
    },
    "agent4": {
      "status": "pending",
      "output": null,
      "error": null
    }
  },
  "control": {
    "current_stage": null,
    "status": "pending",
    "stop_reason": null,
    "human_review_required": false
  },
  "errors": []
}
```

## 2. Workflow 状态

```text
pending
running
completed
failed
stopped
```

| 状态 | 含义 |
|---|---|
| `pending` | 尚未开始 |
| `running` | 正在执行 |
| `completed` | 五 Agent 流程正常完成 |
| `failed` | 某个 Agent 阶段异常失败 |
| `stopped` | Workflow Gate 主动停止，例如 required context 失败 |

## 3. Stage 状态

```text
pending
running
success
failed
skipped
```

`stages.<stage_id>.output` 保存 Agent 原始业务输出，不改字段、不改结构。

## 4. Context 状态

`context.items` 保存 Context Provider 返回的 Context Package：

```json
{
  "context_id": "repo_context",
  "provider_id": "understand_domain_repository_context_provider",
  "tool_id": null,
  "skill_id": "understand_domain_repository_context",
  "capability_type": "skill",
  "source": {},
  "required": false,
  "content_type": "repository_context_json",
  "content": "string|null",
  "status": "success|failed",
  "error": null
}
```

Context Tool、Skill 或 Provider 不决定流程是否继续。

## 5. Context 失败策略

失败策略由 Workflow 执行：

```text
required context 失败
-> workflow_state.context.items 记录 failed package
-> workflow_state.errors 记录错误
-> control.status = stopped
-> control.stop_reason = "required context source failed: <source_id>"
-> 所有 pending Agent stage 标记为 skipped
-> Agent1A 不执行
```

```text
optional context 失败
-> workflow_state.context.items 记录 failed package
-> workflow_state.errors 记录错误
-> control.status 保持 running
-> Pipeline 继续
```

## 6. Agent 失败策略

某个 Agent 抛出异常时：

```text
当前 stage = failed
错误写入 stages.<stage_id>.error
错误追加到 errors
control.status = failed
control.stop_reason = "<stage_id> failed"
后续 pending stages = skipped
返回部分业务结果和 Workflow State
```

## 7. 与 Trace 的关系

Workflow State 表示当前状态和最终状态。

Execution Trace 记录实际发生的调用事件。

当前 Trace 文件：

```text
outputs/traces/{run_id}/workflow_events.jsonl
outputs/traces/{run_id}/agent_traces.jsonl
outputs/traces/{run_id}/tool_traces.jsonl
```

一次 run 的完整调用顺序优先由 `workflow_events.jsonl` 还原。

## 8. 边界

- 不做动态路由。
- 只接入一个本地只读 Repository Context Skill。
- 不接 PDF、表格、远程 GitHub 或网络仓库。
- Registry 仍只声明，不参与执行决策。
- 五 Agent 顺序仍由 `core/pipeline_runner.py` 的 `STAGE_ORDER` 固定定义。
