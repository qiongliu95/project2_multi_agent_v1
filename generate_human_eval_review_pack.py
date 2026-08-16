"""Generate a compact Human Semantic Evaluation review pack.

This utility reads existing evaluation outputs and traces, then writes Markdown
review packs for humans. It does not run the workflow, call an LLM judge, or
assign scores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent

CASES = [
    "case_01_complete_requirement",
    "case_02_incomplete_requirement",
    "case_03_complex_rule_requirement",
]

STAGE_KEYS = {
    "Agent1A": "agent_1_parsing",
    "Agent1B": "agent_1_questions",
    "Agent2": "agent_2_risk",
    "Agent3": "agent_3_test",
    "Agent4": "agent_4_summary",
}

CONTEXT_VERSIONS = ["A_text_only", "B_structured_context", "C_compiler_context"]

CRITERIA = [
    "Grounding",
    "Boundary Compliance",
    "Completeness",
    "Uncertainty Handling",
    "Relevance",
    "Usefulness",
]


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_text(errors="replace")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in read_text(path).splitlines() if line.strip())


def truncate(value: Any, limit: int = 220) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def list_count(obj: Dict[str, Any], keys: Iterable[str]) -> int:
    total = 0
    for key in keys:
        value = obj.get(key)
        if isinstance(value, list):
            total += len(value)
    return total


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def comparison_run_dir(case_id: str, version: str) -> Path:
    return ROOT / "outputs" / "context_comparison_p1_real" / case_id / version


def load_run_result(run_dir: Path) -> Tuple[Optional[Dict[str, Any]], Path]:
    path = run_dir / "final_result.json"
    if not path.exists():
        return None, path
    return read_json(path), path


def workflow_status(final_result: Optional[Dict[str, Any]]) -> Tuple[str, Optional[str]]:
    if not final_result:
        return "missing", "missing final_result.json"
    state = final_result.get("workflow_state") or {}
    if isinstance(state.get("control"), dict):
        control = state["control"]
        status = control.get("status") or state.get("status")
        stop_reason = control.get("stop_reason") or state.get("stop_reason")
        return status or "unknown", stop_reason
    return state.get("status") or "unknown", state.get("stop_reason")


def stage_summary(final_output: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    agent1a = final_output.get("agent_1_parsing") or {}
    agent1b = final_output.get("agent_1_questions") or {}
    agent2 = final_output.get("agent_2_risk") or {}
    agent3 = final_output.get("agent_3_test") or {}
    agent4 = final_output.get("agent_4_summary") or {}

    gaps = agent1a.get("action_gap_candidates") or []
    specific_unknowns = []
    context_refs = []
    for gap in gaps:
        if isinstance(gap, dict):
            specific_unknowns.extend(as_list(gap.get("specific_unknowns")))
            context_refs.extend(as_list(gap.get("context_refs")))

    risk_items = agent2.get("risk_items") or []
    risk_arrays = [
        "ambiguity_risks",
        "missing_info",
        "edge_case_risks",
        "permission_risks",
        "data_risks",
        "performance_risks",
    ]
    test_fields = [
        "core_test_points",
        "edge_test_points",
        "performance_test_points",
        "acceptance_criteria",
        "functional_test_points",
        "boundary_test_points",
        "risk_based_test_points",
    ]

    return {
        "Agent1A": {
            "main_flow": len(as_list(agent1a.get("main_flow"))),
            "known_conditions": sum(
                len(as_list(g.get("known_conditions"))) for g in gaps if isinstance(g, dict)
            ),
            "specific_unknowns": len(specific_unknowns),
            "context_refs": len(set(str(x) for x in context_refs)),
            "sample_unknowns": specific_unknowns[:5],
        },
        "Agent1B": {
            "open_questions": len(as_list(agent1b.get("open_questions"))),
            "question_sources": len(as_list(agent1b.get("question_sources"))),
            "sample_questions": as_list(agent1b.get("open_questions"))[:5],
        },
        "Agent2": {
            "risk_items": len(risk_items),
            "risk_arrays_total": list_count(agent2, risk_arrays),
            "sample_risks": risk_items[:5] if risk_items else [],
        },
        "Agent3": {
            "test_focus_total": list_count(agent3, test_fields),
            "sample_test_focus": (
                as_list(agent3.get("core_test_points"))
                + as_list(agent3.get("functional_test_points"))
                + as_list(agent3.get("risk_based_test_points"))
            )[:5],
        },
        "Agent4": {
            "human_review_required": agent4.get("human_review_required"),
            "critical_open_questions": len(as_list(agent4.get("critical_open_questions"))),
        },
    }


def readiness_for_run(run_dir: Path, final_result: Optional[Dict[str, Any]]) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    nonblocking: List[str] = []
    if final_result is None:
        blocking.append("missing final_result.json")
        return "FAIL", blocking, nonblocking

    final_output = final_result.get("final_output") or {}
    missing_stage = [name for name, key in STAGE_KEYS.items() if final_output.get(key) is None]
    if missing_stage:
        blocking.append("missing final output: " + ", ".join(missing_stage))

    trace_dir = run_dir / "workflow_trace"
    if not trace_dir.exists():
        trace_dir = run_dir / "trace"
    if not trace_dir.exists():
        blocking.append("missing trace dir")
    else:
        agent_traces = jsonl_count(trace_dir / "agent_traces.jsonl")
        events = jsonl_count(trace_dir / "workflow_events.jsonl")
        if agent_traces < 5:
            blocking.append(f"incomplete agent trace: {agent_traces}/5")
        if events == 0:
            blocking.append("empty workflow events")
        if not (trace_dir / "tool_traces.jsonl").exists():
            nonblocking.append("tool trace absent; expected for Text Only, optional for archived runs")

    workflow_state = final_result.get("workflow_state") or {}
    if "status" not in workflow_state and "control" not in workflow_state:
        nonblocking.append("workflow status not archived at top level; use final outputs and traces")

    return ("PASS" if not blocking else "FAIL"), blocking, nonblocking


def comparison_row(metrics: Dict[str, Any]) -> List[str]:
    return [
        str(metrics.get("run_id", "")),
        str(metrics.get("status", "")),
        str(metrics.get("stop_reason", "")),
        str(metrics.get("specific_unknown_count", "")),
        str(metrics.get("agent1a_context_ref_count", "")),
        str(metrics.get("agent1b_question_count", "")),
        str(metrics.get("risk_item_count", "")),
        str(metrics.get("risk_items_context_ref_count", "")),
        str(metrics.get("agent3_output_counts", {})),
    ]


def metrics_from_result(final_result: Optional[Dict[str, Any]], run_dir: Path) -> Dict[str, Any]:
    status, stop_reason = workflow_status(final_result)
    if not final_result:
        return {
            "run_id": "",
            "status": status,
            "stop_reason": stop_reason,
            "specific_unknown_count": 0,
            "agent1a_context_ref_count": 0,
            "agent1b_question_count": 0,
            "risk_item_count": 0,
            "risk_items_context_ref_count": 0,
            "agent3_output_counts": {},
            "final_result_path": rel(run_dir / "final_result.json"),
            "trace_path": rel(run_dir / "trace"),
        }

    final_output = final_result.get("final_output") or {}
    summary = stage_summary(final_output)
    agent2 = final_output.get("agent_2_risk") or {}
    agent3 = final_output.get("agent_3_test") or {}
    risk_items = agent2.get("risk_items") or []
    risk_context_refs = []
    for risk in risk_items:
        if isinstance(risk, dict):
            risk_context_refs.extend(as_list(risk.get("context_refs")))

    agent3_fields = [
        "core_test_points",
        "edge_test_points",
        "performance_test_points",
        "acceptance_criteria",
        "test_case_drafts",
        "functional_test_points",
        "boundary_test_points",
        "risk_based_test_points",
    ]
    agent3_counts = {
        key: len(as_list(agent3.get(key)))
        for key in agent3_fields
        if key in agent3
    }

    readiness, blocking, nonblocking = readiness_for_run(run_dir, final_result)
    if readiness == "FAIL":
        status = "failed"
        if not stop_reason:
            stop_reason = "; ".join(blocking)
    elif status in ("unknown", None):
        status = "completed"

    return {
        "run_id": final_result.get("run_id", ""),
        "status": status,
        "stop_reason": stop_reason,
        "specific_unknown_count": summary["Agent1A"]["specific_unknowns"],
        "agent1a_context_ref_count": summary["Agent1A"]["context_refs"],
        "agent1b_question_count": summary["Agent1B"]["open_questions"],
        "risk_item_count": summary["Agent2"]["risk_items"],
        "risk_items_context_ref_count": len(set(str(x) for x in risk_context_refs)),
        "agent3_output_counts": agent3_counts,
        "final_result_path": rel(run_dir / "final_result.json"),
        "trace_path": rel(run_dir / "trace"),
        "readiness": readiness,
        "blocking": blocking,
        "nonblocking": nonblocking,
    }


def load_case_runs(case_id: str) -> Dict[str, Dict[str, Any]]:
    runs: Dict[str, Dict[str, Any]] = {}
    for version in CONTEXT_VERSIONS:
        run_dir = comparison_run_dir(case_id, version)
        result, result_path = load_run_result(run_dir)
        runs[version] = {
            "run_dir": run_dir,
            "result": result,
            "result_path": result_path,
            "metrics": metrics_from_result(result, run_dir),
        }
    return runs


def candidate_cues(case_id: str, summary: Dict[str, Dict[str, Any]], context_case: Dict[str, Any]) -> List[str]:
    cues: List[str] = []
    agent1a = summary.get("Agent1A", {})
    agent1b = summary.get("Agent1B", {})
    agent2 = summary.get("Agent2", {})
    agent3 = summary.get("Agent3", {})

    if agent1a.get("specific_unknowns", 0) == 0 and "incomplete" in case_id:
        cues.append("review_required: 信息不足 case 中 Agent1A 未产生 specific_unknowns，人工复核 Uncertainty Handling / Completeness。")
    if agent1b.get("open_questions", 0) != agent1b.get("question_sources", 0):
        cues.append("review_required: Agent1B open_questions 与 question_sources 数量不一致，人工复核 Grounding。")
    if agent2.get("risk_items", 0) == 0:
        cues.append("review_required: Agent2 未产生 risk_items，人工复核 Completeness / Usefulness。")
    if agent3.get("test_focus_total", 0) == 0:
        cues.append("review_required: Agent3 验证关注点为空，人工复核 Usefulness。")

    if context_case:
        b = context_case.get("B_structured_context", {})
        c = context_case.get("C_compiler_context", {})
        if b.get("status") == "completed" and c.get("status") == "completed":
            if b.get("specific_unknown_count") != c.get("specific_unknown_count"):
                cues.append("review_required: B/C specific_unknown_count 不同；只能作为线索，需人工判断是否为信息丢失、合并或合理收敛。")
            if b.get("risk_item_count") != c.get("risk_item_count"):
                cues.append("review_required: B/C risk_item_count 不同；需人工判断 risk 方向是否发生语义偏移。")
        elif c:
            cues.append("review_required: Compiler 路径未完整完成或缺少可用 metrics，不能用于 B/C 语义比较结论。")

    if not cues:
        cues.append("no automatic review_required signal; still requires human scoring.")
    return cues


def render_case(case_id: str, output_dir: Path) -> None:
    case_runs = load_case_runs(case_id)
    primary_run = case_runs["A_text_only"]
    result = primary_run["result"]
    result_path = primary_run["result_path"]
    final_output = (result or {}).get("final_output") or {}
    summary = stage_summary(final_output)
    run_dir = primary_run["run_dir"]
    readiness, blocking, nonblocking = readiness_for_run(run_dir, result)
    context_case = {version: case_runs[version]["metrics"] for version in CONTEXT_VERSIONS}

    requirement_path = ROOT / "data" / "evaluation_cases" / case_id / "requirement.md"
    expected_path = ROOT / "data" / "evaluation_cases" / case_id / "expected_focus.md"
    scorecard_path = ROOT / "docs" / "human_evaluation_scorecards" / f"{case_id}_scorecard.md"

    lines: List[str] = []
    lines.append(f"# 人工语义评估审阅包 - {case_id}")
    lines.append("")
    lines.append("## 1. 评估边界")
    lines.append("")
    lines.append("- 本文件只辅助人工语义评估，不自动评分。")
    lines.append("- 评分仍使用六个 Criteria：Grounding、Boundary Compliance、Completeness、Uncertainty Handling、Relevance、Usefulness。")
    lines.append("- Overall 与 Blocking 由人工根据证据判断。")
    lines.append("")
    lines.append("## 2. 证据来源与 run 绑定")
    lines.append("")
    lines.append(f"- Requirement：`{rel(requirement_path)}`")
    lines.append(f"- Expected focus：`{rel(expected_path)}`")
    lines.append(f"- Scorecard：`{rel(scorecard_path)}`")
    lines.append("- 页面主体使用 `A_text_only` run；A/B/C Snapshot 分别使用下表绑定的 run 与 `final_result.json` 计算。")
    lines.append("")
    lines.append("| Version | run_id | final_result | trace |")
    lines.append("|---|---|---|---|")
    for version in CONTEXT_VERSIONS:
        metrics = context_case[version]
        lines.append(
            f"| {version} | `{metrics.get('run_id', '')}` | `{metrics.get('final_result_path', '')}` | `{metrics.get('trace_path', '')}` |"
        )
    lines.append("")
    lines.append("## 3. Minimal System Readiness")
    lines.append("")
    lines.append(f"- Result: `{readiness}`")
    lines.append(f"- Blocking: {blocking or ['none']}")
    lines.append(f"- Non-blocking: {nonblocking or ['none']}")
    lines.append("")
    lines.append("## 4. A_text_only Agent 关键输出摘要")
    lines.append("")
    lines.append("| Agent | 摘要 | 人工关注点 |")
    lines.append("|---|---|---|")
    lines.append(
        f"| Agent1A | main_flow={summary['Agent1A']['main_flow']}; known_conditions={summary['Agent1A']['known_conditions']}; specific_unknowns={summary['Agent1A']['specific_unknowns']}; context_refs={summary['Agent1A']['context_refs']} | 检查需求拆解与 unknown 是否合理。 |"
    )
    lines.append(
        f"| Agent1B | open_questions={summary['Agent1B']['open_questions']}; question_sources={summary['Agent1B']['question_sources']} | 检查澄清问题是否来源于 Agent1A Artifact。 |"
    )
    lines.append(
        f"| Agent2 | risk_items={summary['Agent2']['risk_items']}; old risk arrays total={summary['Agent2']['risk_arrays_total']} | 检查风险是否基于需求、unknown 或规则。 |"
    )
    lines.append(
        f"| Agent3 | validation output count={summary['Agent3']['test_focus_total']} | 检查 unknown 是否被当成确定事实生成验证点。 |"
    )
    lines.append(
        f"| Agent4 | human_review_required={summary['Agent4']['human_review_required']}; critical_open_questions={summary['Agent4']['critical_open_questions']} | 检查总结是否以 Stage Artifact 为主。 |"
    )
    lines.append("")
    lines.append("## 5. A_text_only 关键样例")
    lines.append("")
    lines.append("### Agent1A unknown 样例")
    for item in summary["Agent1A"]["sample_unknowns"] or ["none"]:
        lines.append(f"- {truncate(item)}")
    lines.append("")
    lines.append("### Agent1B 问题样例")
    for item in summary["Agent1B"]["sample_questions"] or ["none"]:
        lines.append(f"- {truncate(item)}")
    lines.append("")
    lines.append("### Agent2 risk_items 样例")
    for item in summary["Agent2"]["sample_risks"] or ["none"]:
        lines.append(f"- {truncate(item)}")
    lines.append("")
    lines.append("### Agent3 验证关注点样例")
    for item in summary["Agent3"]["sample_test_focus"] or ["none"]:
        lines.append(f"- {truncate(item)}")
    lines.append("")
    lines.append("## 6. A/B/C Context Path Snapshot")
    lines.append("")
    lines.append("| Version | run_id | status | stop_reason | unknowns | context_refs | questions | risk_items | risk_context_refs | agent3_counts |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---|")
    for version in CONTEXT_VERSIONS:
        metrics = context_case.get(version, {})
        row = comparison_row(metrics)
        lines.append(f"| {version} | " + " | ".join(row) + " |")
    lines.append("")
    lines.append("> 数量变化只是证据线索，不能自动证明 Context 改善了结果。")
    lines.append("")
    lines.append("## 7. AI 辅助复核线索")
    lines.append("")
    for cue in candidate_cues(case_id, summary, context_case):
        lines.append(f"- {cue}")
    lines.append("")
    lines.append("## 8. 人工评分工作区")
    lines.append("")
    lines.append("| Criteria | Score 0/1/2 | Evidence notes | Reviewer notes |")
    lines.append("|---|---:|---|---|")
    for criterion in CRITERIA:
        lines.append(f"| {criterion} |  |  |  |")
    lines.append("")
    lines.append("Overall:")
    lines.append("")
    lines.append("- [ ] Pass")
    lines.append("- [ ] Partial")
    lines.append("- [ ] Fail")
    lines.append("")
    lines.append("Blocking:")
    lines.append("")
    lines.append("- [ ] Yes")
    lines.append("- [ ] No")
    lines.append("")
    lines.append("Reviewer notes:")
    lines.append("")
    lines.append("```text")
    lines.append("")
    lines.append("```")

    (output_dir / f"{case_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def render_index(output_dir: Path) -> None:
    lines = [
        "# 人工语义评估审阅包",
        "",
        "本目录汇总现有评估证据，用于降低人工语义评估的阅读成本。",
        "",
        "它不会运行 Workflow、调用 LLM Judge、自动打分或修改任何项目输出。",
        "",
        "## Cases",
        "",
        "| Case | Review Pack | Scorecard | Context metrics available |",
        "|---|---|---|---|",
    ]
    for case_id in CASES:
        pack = output_dir / f"{case_id}.md"
        scorecard = ROOT / "docs" / "human_evaluation_scorecards" / f"{case_id}_scorecard.md"
        has_runs = all(comparison_run_dir(case_id, version).exists() for version in CONTEXT_VERSIONS)
        lines.append(
            f"| {case_id} | `{rel(pack)}` | `{rel(scorecard)}` | {'yes' if has_runs else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## 使用方式",
            "",
            "1. 先打开对应 case 的 review pack。",
            "2. 通过关键摘要和 AI 辅助复核线索定位需要查看的位置。",
            "3. 只有当评分或问题判断需要证据时，再下钻原始 output 或 trace。",
            "4. 最终由人工填写官方 scorecard 或本文末尾的工作区。",
            "",
            "## 人工判断边界",
            "",
            "- 自动摘要和线索只是 `review_required` 证据。",
            "- 六个 Criteria 的评分、Overall 和 Blocking 均由人工决定。",
            "- unknown、context_refs、risk_items 或测试关注点数量变化本身不是质量结论。",
        ]
    )
    (output_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate human evaluation review pack from existing outputs.")
    parser.add_argument("--output-dir", default="outputs/human_eval_review_pack")
    parser.add_argument("--case", choices=CASES, action="append", help="Generate only selected case; can be repeated.")
    args = parser.parse_args()

    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_cases = args.case or CASES
    for case_id in selected_cases:
        render_case(case_id, output_dir)
    render_index(output_dir)
    print(f"Generated review pack: {output_dir}")
    for case_id in selected_cases:
        print(f"- {output_dir / (case_id + '.md')}")


if __name__ == "__main__":
    main()
