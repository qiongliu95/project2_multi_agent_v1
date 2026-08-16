# Context Comparison Baseline

> 文档状态：历史方法参考。最终 Evaluation MVP 和结项判断口径以 `docs/evaluation_mvp_final.md` 为准；本文不再单独作为项目停止标准。

## Purpose

This baseline verifies whether Context View improves the current five-Agent requirement analysis workflow.

It is not a model benchmark, an evaluation platform, or an automatic quality scoring system. It only preserves a repeatable comparison of the same evaluation cases across three input paths:

| Version | Meaning |
|---|---|
| A_text_only | Current requirement only, no Context. |
| B_structured_context | Hand-maintained Context Package V2. |
| C_compiler_context | Human Context Markdown compiled into Context Package V2. |

## Scope

The baseline answers these questions:

- Does Agent1A produce fewer broad gaps and more specific unknowns?
- Are specific unknowns connected to Context item IDs?
- Does Agent1B continue to generate questions from Agent1A Stage Artifact?
- Does Agent2 produce `risk_items` with related unknowns, rules, constraints, and context refs?
- Does Agent3 maintain validation focus without losing risk-driven points?

The baseline does not answer:

- Which LLM is better.
- Whether generated test cases are complete.
- Whether enterprise knowledge is complete.
- Whether Auto Context should be expanded.

## Command

Run all three cases and all three input versions:

```bash
python evaluate_context_comparison.py --agent-mode real --output-root outputs/context_comparison_baseline
```

Use fake mode only when API configuration or network access blocks real Agent execution:

```bash
python evaluate_context_comparison.py --agent-mode fake --output-root outputs/context_comparison_baseline_fake
```

Summarize an existing run without re-running Agents:

```bash
python evaluate_context_comparison.py --skip-run --output-root outputs/context_comparison_baseline
```

Run one case only:

```bash
python evaluate_context_comparison.py --agent-mode real --case case_02_incomplete_requirement --output-root outputs/context_comparison_case02
```

## Output

Each run writes:

```text
outputs/context_comparison_baseline/
├── compiled_context/
├── case_01_complete_requirement/
│   ├── A_text_only/
│   ├── B_structured_context/
│   └── C_compiler_context/
├── case_02_incomplete_requirement/
├── case_03_complex_rule_requirement/
├── summary_metrics.json
└── summary.md
```

Each version directory contains:

- `final_result.json`
- `agent1a_output.json`
- `agent1b_output.json`
- `agent2_output.json`
- `agent3_output.json`
- `agent4_output.json`
- `trace/`
- `run.log`
- `exit_code.txt`

## Metrics

`summary_metrics.json` records:

- Workflow status and stop reason.
- Context item counts by section.
- Agent1A main flow count, known condition count, specific unknown count, unassigned unknown count, and context ref count.
- Heuristic unknown type counts:
  - `business_decision_gap`
  - `rule_gap`
  - `constraint_gap`
  - `implementation_detail_gap`
- Agent1B question count and question source count.
- Agent2 old risk array counts and `risk_items` counts.
- `risk_items` related unknown/rule/constraint/context ref counts.
- Agent3 output item counts.
- Per-agent trace context consumption.

## Reading Rule

The most important comparison is not raw output volume. The useful signal is:

```text
Text only
→ broad or unsupported gaps

Structured / Compiler Context
→ specific unknowns + known conditions + source-linked risk_items
```

If Context increases output length but does not increase specificity or traceability, it is not improving the workflow.

## Boundaries

This baseline intentionally does not modify:

- Agent count.
- Pipeline order.
- Runtime Context Package V2 schema.
- Agent Prompt.
- Context View configuration.
- Auto Context release gates.
