# Context Source V1

本文档说明当前最小上下文接入机制。

当前支持两类 Context Source：

- `local_markdown`：本地 Markdown Tool。
- `local_repository`：一个受限接入的本地只读 Repository Context Skill。

本阶段仍不接入 PDF、表格、远程 GitHub、网络仓库或多个 External Skill。

## 1. Context Source

Markdown 示例：

```json
{
  "source_id": "product_context",
  "type": "local_markdown",
  "path": "data/context/product_context.md",
  "required": false
}
```

Repository 示例：

```json
{
  "source_id": "repo_context",
  "type": "local_repository",
  "path": ".",
  "required": false
}
```

字段说明：

| 字段 | 含义 |
|---|---|
| `source_id` | 上下文来源 ID |
| `type` | `local_markdown` 或 `local_repository` |
| `path` | 本地文件或本地仓库目录路径 |
| `required` | 是否为必需上下文，默认 `false` |

来源可以配置在：

- `configs/pipeline_config.json` 的 `context_sources`
- 单个 case 的 `context_sources`

纯文本路径保持兼容：

```json
{
  "context_sources": []
}
```

## 2. Context Provider

Pipeline 只通过统一入口调用 Context Provider：

```text
core.context_tools.load_context_source(source)
```

Pipeline 不直接判断 Markdown、Repository 或 Skill 的内部处理细节。

当前 Provider：

| source type | provider_id | capability_type | capability |
|---|---|---|---|
| `local_markdown` | `local_markdown_context_provider` | `tool` | `local_markdown_context_reader` |
| `local_repository` | `understand_domain_repository_context_provider` | `skill` | `understand_domain_repository_context` |

Provider 只返回处理结果，不决定 Workflow 是否继续。

## 3. Repository Context Skill

本次接入的 External Skill 来自本地 Codex skill 源码：

```text
C:/Users/12643/.codex/skills/understand-domain/extract-domain-context.py
```

接入方式：

- `core/context_tools.py` 只调用 Repository Context Adapter，不直接了解 Skill 内部函数。
- Adapter 文件：`core/repository_context_skill_adapter.py`。
- Adapter 负责 Skill 路径解析、模块加载、接口校验、函数调用、结果转换和失败包装。
- 不调用 Skill CLI 的 `main()`。
- 不触发子 Agent。
- 不写入目标仓库默认 `.understand-anything` 目录。
- Adapter 只导入并调用已审查的只读扫描函数：
  - `parse_gitignore`
  - `scan_file_tree`
  - `detect_entry_points`
  - `extract_file_signatures`
  - `extract_metadata`
  - `_truncate_to_fit`

安全边界：

```json
{
  "local_only": true,
  "read_only": true,
  "network_access": false,
  "shell_commands": false,
  "writes_to_repository": false
}
```

当前实现还限制 `local_repository.path` 必须位于项目根目录内。

Adapter 会在 Context Package 中记录 Skill 来源信息：

```json
{
  "skill_metadata": {
    "declared_source": "C:/Users/12643/.codex/skills/understand-domain/extract-domain-context.py",
    "loaded_path": "C:/Users/12643/.codex/skills/understand-domain/extract-domain-context.py",
    "version": null,
    "fingerprint": {
      "sha256": "string",
      "size_bytes": 0,
      "modified_at": "string"
    }
  }
}
```

## 4. Context Package

所有 Provider 输出都统一转换为 Context Package。

Markdown 成功：

```json
{
  "context_id": "product_context",
  "provider_id": "local_markdown_context_provider",
  "tool_id": "local_markdown_context_reader",
  "skill_id": null,
  "capability_type": "tool",
  "required": false,
  "content_type": "markdown",
  "content": "string",
  "status": "success",
  "error": null
}
```

Repository Skill 成功：

```json
{
  "context_id": "repo_context",
  "provider_id": "understand_domain_repository_context_provider",
  "tool_id": null,
  "skill_id": "understand_domain_repository_context",
  "capability_type": "skill",
  "required": false,
  "content_type": "repository_context_json",
  "content": "{...}",
  "status": "success",
  "error": null
}
```

失败时仍返回 Context Package，并写入 `workflow_state.errors`：

```json
{
  "context_id": "repo_context",
  "provider_id": "understand_domain_repository_context_provider",
  "skill_id": "understand_domain_repository_context",
  "capability_type": "skill",
  "required": true,
  "content_type": "local_repository",
  "content": null,
  "status": "failed",
  "error": {
    "stage_id": "context:repo_context",
    "error_type": "ValueError",
    "message": "string"
  }
}
```

## 5. 失败策略

失败策略由 Workflow 执行，不由 Tool、Skill 或 Provider 决定。

```text
required=true 且处理失败
-> Workflow status = stopped
-> pending Agent stages = skipped
-> Agent1A 不执行
```

```text
required=false 或缺省，且处理失败
-> 记录 context error
-> Workflow 继续执行
-> Agent1A 使用原始 requirement_text 和其他成功 context
```

## 6. 如何传给 Agent1A

如果没有成功读取的 context item：

```text
Agent1A requirement_text = 原始 requirement_text
```

如果存在成功 context：

```text
Agent1A requirement_text = 原始 requirement_text + 补充上下文材料
```

下游 Agent 不直接读取 Context Package，而是继续消费既有 Agent 输出。

## 7. Trace

Context Provider 调用会写入统一事件流：

```text
outputs/traces/{run_id}/workflow_events.jsonl
```

事件通过 `capability_type` 区分能力类型：

```json
{
  "event_type": "skill",
  "capability_type": "skill",
  "name": "understand_domain_repository_context"
}
```

同时保留兼容视图：

```text
outputs/traces/{run_id}/agent_traces.jsonl
outputs/traces/{run_id}/tool_traces.jsonl
```

## 8. 当前未实现

- PDF 读取
- 表格读取
- 远程 GitHub / 网络仓库上下文
- 多个 External Skill 同时接入
- 动态路由
- 通用插件框架
- Agent 自主选择 Skill
