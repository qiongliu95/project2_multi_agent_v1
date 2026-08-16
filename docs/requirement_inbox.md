# Requirement Inbox

## Purpose

`run_requirement_inbox.py` is the real-use entry point for the current Multi-Agent requirement analysis workflow.

Product or test users only need to place Markdown requirement files in:

```text
data/requirements_inbox/
```

Each `.md` file is treated as one independent requirement and is run through the existing five-Agent workflow.

## Run

Run every Markdown file in the default inbox:

```bash
python run_requirement_inbox.py
```

Run a specific directory:

```bash
python run_requirement_inbox.py --input-dir data/requirements_inbox --agent-mode real
```

Run one file in fake mode:

```bash
python run_requirement_inbox.py --file data/requirements_inbox/example.md --agent-mode fake
```

Fake mode is only for observing workflow structure. Fake Agent output is not model output.

## Phase 1 Boundary

This first inbox version is text-only:

```text
requirement markdown
    ↓
read file content
    ↓
build workflow case input
    ↓
run existing run_pipeline_with_state
    ↓
save outputs
```

It does not perform Context matching, Human Context compilation, Auto Context retrieval, RAG, embedding, database lookup, or any Agent routing.

## Outputs

Each requirement run writes to:

```text
outputs/requirement_runs/{run_id}/
```

Saved files:

- `final_result.json`
- `agent1a_output.json`
- `agent1b_output.json`
- `agent2_output.json`
- `agent3_output.json`
- `agent4_output.json`
- `workflow_events.jsonl`
- `agent_traces.jsonl`
- `run_summary.md`

`final_result.json` preserves:

- `run_id`
- `case_id`
- `source_file`
- `agent_mode`
- `original_requirement_text`
- `final_output`
- `workflow_state`

## Current Limitations

- Only local Markdown files are supported.
- Context sources are always empty in Phase 1.
- If real Agent execution fails because of API or network issues, the failure is recorded and the script continues to the next file.
- The script does not modify Agent prompts, Agent order, Context View, Runtime Context V2 schema, or Agent output schemas.
