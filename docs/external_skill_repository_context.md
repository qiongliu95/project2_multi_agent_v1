# Repository Context Skill 接入审查

## 1. 选择结果

本次选择：

```text
understand_domain_repository_context
```

源码来源：

```text
C:/Users/12643/.codex/skills/understand-domain/extract-domain-context.py
```

选择原因：

- 它是已有本地 Codex Skill 的真实源码，不是项目内临时伪 Skill。
- 能读取本地代码库并生成结构化 repository context。
- 能提供普通文件读取 Tool 不具备的处理能力：文件树扫描、入口点识别、文件签名提取、元数据聚合、上下文截断。
- 可限制为本地只读函数调用，不需要联网、不需要 shell、不需要修改被分析仓库。

## 2. 未选择的候选

`github_context` 暂不接入。

原因：

- 当前边界要求本地、只读、可追踪。
- 远程 GitHub Issue、PR、README 或仓库抓取涉及网络访问和认证边界。
- 本阶段不做远程上下文、动态路由或插件平台。

完整 `/understand` Skill 暂不直接接入。

原因：

- 默认会写 `.understand-anything`。
- 可能触发依赖安装或构建。
- 可能触发子 Agent。
- 超出本阶段“只读 Context Provider”的目标。

## 3. 安全和副作用审查

审查对象：

```text
extract-domain-context.py
```

默认 CLI 行为：

- 读取本地项目文件。
- 写入 `<project-root>/.understand-anything/intermediate/domain-context.json`。

本项目适配方式：

- `core/context_tools.py` 不直接加载 Skill 源码。
- Skill 路径解析、模块加载、接口校验、函数调用和结果转换集中在 `core/repository_context_skill_adapter.py`。
- 不调用 `main()`。
- 不使用默认输出路径。
- 不执行 shell 命令。
- 不联网。
- Adapter 只导入并调用只读函数：
  - `parse_gitignore`
  - `scan_file_tree`
  - `detect_entry_points`
  - `extract_file_signatures`
  - `extract_metadata`
  - `_truncate_to_fit`

当前适配层还限制 repository path 必须位于项目根目录内。

Adapter 会记录：

- `declared_source`
- `loaded_path`
- `required_functions`
- `version`
- `fingerprint.sha256`
- `fingerprint.size_bytes`
- `fingerprint.modified_at`

Skill 缺失、加载失败或接口函数缺失时，Adapter 返回标准 failed Context Package；后续仍由 Workflow 执行 required / optional 策略。

## 4. 接入链路

```text
Context Source(type=local_repository)
-> core.context_tools.load_context_source
-> understand_domain_repository_context_provider
-> core.repository_context_skill_adapter
-> understand_domain_repository_context
-> Context Package(content_type=repository_context_json)
-> Workflow State context.items
-> workflow_events.jsonl(capability_type=skill)
-> Agent1A receives augmented requirement_text
-> existing five-Agent Pipeline continues
```

## 5. 输出 Artifact

Repository Skill 输出被统一转换为 Context Package：

```json
{
  "context_id": "repo_context",
  "provider_id": "understand_domain_repository_context_provider",
  "tool_id": null,
  "skill_id": "understand_domain_repository_context",
  "capability_type": "skill",
  "content_type": "repository_context_json",
  "status": "success"
}
```

## 6. 边界

- 不修改五 Agent Prompt。
- 不修改五 Agent 业务 Schema。
- 不修改五 Agent 执行顺序。
- 不让 Registry 参与调度。
- 不让 Agent 自主选择 Skill。
- 不接入第二个 Skill。
- 不接入远程仓库。
