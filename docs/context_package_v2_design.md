# Context Package V2 Design

## Current Problem

Context Package V1 can pass Markdown content into the Workflow, but it is still raw text. Agents must repeatedly infer which statements are known facts, which are business rules, and which items are still unknown. This causes duplicated clarification questions and broad gap detection, even when the Markdown has already answered part of the question.

Context Package V2 keeps context as a structured Workflow information asset. It does not add Agents, RAG, a database, a knowledge graph, or dynamic routing.

## Context Layer Goal

The Context Layer should turn enterprise material into stable sections that Agents can consume with clear boundaries:

- confirmed facts
- business rules
- constraints
- process flows
- unknowns
- source references
- quality flags

The first implementation uses a manually prepared JSON file. Automatic extraction from Markdown is intentionally out of scope.

## Context Package V2 Schema

```json
{
  "context_package_version": "v2",
  "context_id": "registration_context_v2",
  "summary": "Short package summary",
  "structured_content": {
    "confirmed_facts": [
      {
        "id": "fact_login_supported",
        "text": "当前系统支持用户登录。",
        "source_ref": "outputs/verify_inputs/markdown_context.md#2-登录功能",
        "confidence": "high"
      }
    ],
    "business_rules": [],
    "constraints": [],
    "process_flows": [],
    "unknowns": [],
    "source_refs": [],
    "quality_flags": []
  }
}
```

Minimum validation only checks that required sections exist, every section is a list, and every item has `id` and `text`.

## Context Processor Design

First version:

```text
local_structured_context JSON
        ↓
local_structured_context_provider
        ↓
Context Package V2
        ↓
Workflow State
```

The provider only reads and normalizes the package. It does not decide whether the Workflow continues. Existing required / optional failure policy remains owned by Workflow.

## Agent Input Contract V2

Workflow State keeps the original `requirement_text` unchanged. Before each Agent call, Pipeline builds an Agent-specific `context_view` and then renders a temporary Agent input from:

```text
original requirement_text + current Agent context_view
```

Agent1A consumes confirmed facts, business rules, constraints, process flows, and unknowns. Unknowns are only known missing items, not confirmed facts.

Agent1B consumes known facts/rules/constraints plus unknowns, so clarification questions should focus on unknowns instead of repeating known rules.

Agent2 consumes known rules, constraints, flows, unknowns, and quality flags for evidence-bound risk analysis.

Agent3 consumes known rules, constraints, flows, and unknowns. Unknowns can only be represented as information gaps, not final assertions.

Agent4 consumes all structured sections needed to summarize confirmed results, remaining unknowns, source refs, and human review needs.

## Trace Fields

Agent trace keeps compatibility fields and adds:

```json
{
  "original_requirement_ref": "workflow_state.input.requirement_text",
  "context_view": {},
  "context_consumption": [
    {
      "context_id": "registration_context_v2",
      "section": "business_rules",
      "item_ids": ["rule_phone_unique"]
    }
  ],
  "final_input_sources": [
    "workflow_state.input.requirement_text",
    "agent_context_view.agent1a.business_rules.rule_phone_unique"
  ]
}
```

This is not a conclusion-level evidence chain. It only records which Context items were available to each Agent.

## Data Flow

```text
Input requirement_text
        ↓
Context Source
        ↓
Context Package V2
        ↓
Workflow State
        ↓
Agent-specific Context View
        ↓
Rendered Agent Input
        ↓
Agent1A → Agent1B → Agent2 → Agent3 → Agent4
        ↓
Execution Trace
```

## Verification

Run the three fake smoke tests:

```bash
python verify_workflow.py --mode text --agent-mode fake
python verify_workflow.py --mode markdown --agent-mode fake
python verify_workflow.py --mode structured --agent-mode fake
```

Expected observation:

- text mode has no Context Package.
- markdown mode keeps the V1 raw Markdown path.
- structured mode records Context Package V2, Agent Context Views, consumed item IDs, and final input sources.
- Workflow State input requirement remains unchanged.

Real model comparison can be run later with:

```bash
python verify_workflow.py --mode text
python verify_workflow.py --mode markdown
python verify_workflow.py --mode structured
```

No automatic result scoring is implemented.

## Later Work

- Add a deterministic or LLM-assisted Context Processor after the manual V2 format is understood.
- Add schema validation as a Tool only after the V2 shape stabilizes.
- Add evidence checking only when output-level traceability becomes necessary.
