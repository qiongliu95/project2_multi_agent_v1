"""
Run and summarize the Context View comparison baseline.

This script is intentionally outside the production workflow. It reuses
verify_workflow.py, Context Package V2, and the existing trace output to create
a repeatable evidence set for Text vs Structured vs Human Compiler Context.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.context_compiler import compile_human_context_file, save_compiled_context


PROJECT_ROOT = Path(__file__).resolve().parent

STAGE_OUTPUTS = {
    "agent1a": "agent_1_parsing",
    "agent1b": "agent_1_questions",
    "agent2": "agent_2_risk",
    "agent3": "agent_3_test",
    "agent4": "agent_4_summary",
}

CASES = {
    "case_01_complete_requirement": {
        "requirement": "data/evaluation_cases/case_01_complete_requirement/requirement.md",
        "structured_context": "data/context/evaluation/case_01_structured_context_v2.json",
        "human_context": "data/human_context/evaluation/case_01_email_binding.md",
        "compiled_name": "case_01_compiler_context_v2.json",
    },
    "case_02_incomplete_requirement": {
        "requirement": "data/evaluation_cases/case_02_incomplete_requirement/requirement.md",
        "structured_context": "data/context/evaluation/case_02_structured_context_v2.json",
        "human_context": "data/human_context/evaluation/case_02_phone_login.md",
        "compiled_name": "case_02_compiler_context_v2.json",
    },
    "case_03_complex_rule_requirement": {
        "requirement": "data/evaluation_cases/case_03_complex_rule_requirement/requirement.md",
        "structured_context": "data/context/evaluation/case_03_structured_context_v2.json",
        "human_context": "data/human_context/evaluation/case_03_coupon_selection.md",
        "compiled_name": "case_03_compiler_context_v2.json",
    },
}

VERSIONS = {
    "A_text_only": {"mode": "text", "context": None},
    "B_structured_context": {"mode": "structured", "context": "structured_context"},
    "C_compiler_context": {"mode": "structured", "context": "compiled_context"},
}

RISK_ARRAY_FIELDS = [
    "ambiguity_risks",
    "missing_info",
    "edge_case_risks",
    "permission_risks",
    "data_risks",
    "performance_risks",
]

AGENT3_LIST_FIELDS = [
    "core_test_points",
    "edge_test_points",
    "performance_test_points",
    "acceptance_criteria",
    "test_case_drafts",
    "functional_test_points",
    "boundary_test_points",
    "risk_based_test_points",
]


def _json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _read_text(path: str | Path) -> str:
    input_path = Path(path)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    return input_path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def _count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _extract_saved_path(stdout: str, label: str) -> Optional[Path]:
    pattern = re.compile(rf"^{re.escape(label)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(stdout)
    if not match:
        return None
    path = Path(match.group(1).strip())
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _compile_human_contexts(output_root: Path) -> Dict[str, Path]:
    compiled_dir = output_root / "compiled_context"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    compiled_paths: Dict[str, Path] = {}

    for case_id, case_config in CASES.items():
        package = compile_human_context_file(case_config["human_context"])
        output_path = compiled_dir / case_config["compiled_name"]
        save_compiled_context(package, output_path)
        compiled_paths[case_id] = output_path

    return compiled_paths


def _run_verify(
    *,
    case_id: str,
    version_id: str,
    case_config: Dict[str, str],
    compiled_paths: Dict[str, Path],
    agent_mode: str,
    version_output_dir: Path,
) -> Dict[str, Any]:
    version_config = VERSIONS[version_id]
    requirement_text = _read_text(case_config["requirement"])

    cmd = [
        sys.executable,
        "verify_workflow.py",
        "--mode",
        version_config["mode"],
        "--agent-mode",
        agent_mode,
        "--requirement-text",
        requirement_text,
    ]

    context_kind = version_config["context"]
    if context_kind == "structured_context":
        cmd.extend(["--structured-context", str(PROJECT_ROOT / case_config["structured_context"])])
    elif context_kind == "compiled_context":
        cmd.extend(["--structured-context", str(compiled_paths[case_id])])

    version_output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    completed = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    stdout = completed.stdout or ""
    (version_output_dir / "run.log").write_text(stdout, encoding="utf-8")
    (version_output_dir / "exit_code.txt").write_text(
        str(completed.returncode),
        encoding="utf-8",
    )

    result_path = _extract_saved_path(stdout, "result_json")
    trace_dir = _extract_saved_path(stdout, "trace_dir")

    if result_path and result_path.exists():
        shutil.copy2(result_path, version_output_dir / "final_result.json")
        _write_agent_outputs(version_output_dir / "final_result.json", version_output_dir)

    if trace_dir and trace_dir.exists():
        shutil.copytree(trace_dir, version_output_dir / "trace", dirs_exist_ok=True)

    return {
        "case_id": case_id,
        "version": version_id,
        "command": _display_command(case_config, version_id, agent_mode, compiled_paths.get(case_id)),
        "exit_code": completed.returncode,
        "result_json": str(result_path) if result_path else "",
        "trace_dir": str(trace_dir) if trace_dir else "",
        "archived_dir": str(version_output_dir),
    }


def _quote_command_part(part: str) -> str:
    if not part:
        return '""'
    if re.search(r"\s", part):
        return '"' + part.replace('"', '\\"') + '"'
    return part


def _display_command(
    case_config: Dict[str, str],
    version_id: str,
    agent_mode: str,
    compiled_context_path: Optional[Path],
) -> str:
    version_config = VERSIONS[version_id]
    parts = [
        "python",
        "verify_workflow.py",
        "--mode",
        version_config["mode"],
        "--agent-mode",
        agent_mode,
        "--requirement-text",
        f"<{case_config['requirement']}>",
    ]
    context_kind = version_config["context"]
    if context_kind == "structured_context":
        parts.extend(["--structured-context", case_config["structured_context"]])
    elif context_kind == "compiled_context" and compiled_context_path:
        parts.extend(["--structured-context", str(compiled_context_path)])
    return " ".join(_quote_command_part(part) for part in parts)


def _write_agent_outputs(result_path: Path, output_dir: Path) -> None:
    result = _read_json(result_path)
    final_output = result.get("final_output", {})
    for agent_name, output_key in STAGE_OUTPUTS.items():
        output = final_output.get(output_key)
        (output_dir / f"{agent_name}_output.json").write_text(
            _json_dump(output),
            encoding="utf-8",
        )


def _classify_unknown(text: str) -> str:
    lower = text.lower()
    implementation_markers = [
        "接口",
        "页面",
        "按钮",
        "字段格式",
        "存储位置",
        "技术",
        "系统实现",
        "返回码",
    ]
    constraint_markers = ["限制", "不允许", "禁止", "权限", "范围", "只读"]
    business_decision_markers = ["是否", "策略", "优先级", "状态", "处理"]
    rule_markers = ["规则", "有效期", "频率", "次数", "校验", "验证码", "日志"]

    if any(marker in text for marker in implementation_markers):
        return "implementation_detail_gap"
    if any(marker in text for marker in constraint_markers):
        return "constraint_gap"
    if any(marker in text for marker in rule_markers):
        return "rule_gap"
    if any(marker in text for marker in business_decision_markers) or "whether" in lower:
        return "business_decision_gap"
    return "business_decision_gap"


def _iter_agent1a_unknowns(agent1a: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for candidate in _safe_list(agent1a.get("action_gap_candidates")):
        action = candidate.get("action", "")
        context_refs = _safe_list(candidate.get("context_refs"))
        for unknown in _safe_list(candidate.get("specific_unknowns")):
            yield {
                "text": unknown,
                "action": action,
                "context_refs": context_refs,
                "assigned": True,
            }
    for unknown in _safe_list(agent1a.get("unassigned_unknowns")):
        if isinstance(unknown, dict):
            yield {
                "text": unknown.get("text") or unknown.get("unknown") or "",
                "action": "",
                "context_refs": _safe_list(unknown.get("context_refs")),
                "assigned": False,
            }
        else:
            yield {
                "text": str(unknown),
                "action": "",
                "context_refs": [],
                "assigned": False,
            }


def _summarize_context_items(workflow_state: Dict[str, Any]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for item in _safe_list(workflow_state.get("context", {}).get("items")):
        structured = item.get("structured_content") if isinstance(item, dict) else None
        if not isinstance(structured, dict):
            continue
        for section, entries in structured.items():
            if isinstance(entries, list):
                counts[section] += len(entries)
    return dict(counts)


def _summarize_trace_context(trace_dir: Path) -> Dict[str, Dict[str, int]]:
    events = _read_jsonl(trace_dir / "workflow_events.jsonl")
    summary: Dict[str, Dict[str, int]] = {}
    for event in events:
        if event.get("event_type") != "agent":
            continue
        agent_name = str(event.get("name") or event.get("stage") or "unknown")
        payload = event.get("payload") or {}
        section_counts: Counter[str] = Counter()
        for consumed in _safe_list(payload.get("context_consumption")):
            section = consumed.get("section", "unknown")
            section_counts[section] += len(_safe_list(consumed.get("item_ids")))
        summary[agent_name] = dict(section_counts)
    return summary


def _summarize_result(version_dir: Path) -> Dict[str, Any]:
    result_path = version_dir / "final_result.json"
    if not result_path.exists():
        return {
            "status": "missing",
            "exit_code": _read_optional_text(version_dir / "exit_code.txt"),
        }

    result = _read_json(result_path)
    final_output = result.get("final_output", {})
    workflow_state = result.get("workflow_state", {})
    control = workflow_state.get("control", {})

    agent1a = final_output.get("agent_1_parsing") or {}
    agent1b = final_output.get("agent_1_questions") or {}
    agent2 = final_output.get("agent_2_risk") or {}
    agent3 = final_output.get("agent_3_test") or {}

    unknowns = list(_iter_agent1a_unknowns(agent1a if isinstance(agent1a, dict) else {}))
    unknown_type_counts = Counter(
        _classify_unknown(str(item.get("text", ""))) for item in unknowns if item.get("text")
    )
    risk_items = _safe_list(agent2.get("risk_items")) if isinstance(agent2, dict) else []
    risk_type_counts = Counter(
        item.get("risk_type", "unknown") for item in risk_items if isinstance(item, dict)
    )

    agent3_counts = {}
    if isinstance(agent3, dict):
        for field in AGENT3_LIST_FIELDS:
            if field in agent3:
                agent3_counts[field] = _count_list(agent3.get(field))

    risk_array_counts = {}
    if isinstance(agent2, dict):
        for field in RISK_ARRAY_FIELDS:
            risk_array_counts[field] = _count_list(agent2.get(field))

    return {
        "status": control.get("status", "unknown"),
        "stop_reason": control.get("stop_reason"),
        "human_review_required": control.get("human_review_required"),
        "context_item_counts": _summarize_context_items(workflow_state),
        "main_flow_count": _count_list(agent1a.get("main_flow")) if isinstance(agent1a, dict) else 0,
        "known_condition_count": _count_known_conditions(agent1a),
        "specific_unknown_count": sum(1 for item in unknowns if item.get("assigned")),
        "unassigned_unknown_count": sum(1 for item in unknowns if not item.get("assigned")),
        "unknown_type_counts": dict(unknown_type_counts),
        "unknowns": unknowns,
        "agent1a_context_ref_count": _count_agent1a_context_refs(agent1a),
        "agent1b_question_count": _count_list(agent1b.get("open_questions")) if isinstance(agent1b, dict) else 0,
        "question_source_count": _count_list(agent1b.get("question_sources")) if isinstance(agent1b, dict) else 0,
        "risk_array_counts": risk_array_counts,
        "risk_item_count": len(risk_items),
        "risk_type_counts": dict(risk_type_counts),
        "risk_items_related_unknown_count": _count_nested_list_items(risk_items, "related_unknowns"),
        "risk_items_related_rule_count": _count_nested_list_items(risk_items, "related_rules"),
        "risk_items_related_constraint_count": _count_nested_list_items(risk_items, "related_constraints"),
        "risk_items_context_ref_count": _count_nested_list_items(risk_items, "context_refs"),
        "agent3_output_counts": agent3_counts,
        "trace_context_consumption": _summarize_trace_context(version_dir / "trace"),
    }


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _count_known_conditions(agent1a: Any) -> int:
    if not isinstance(agent1a, dict):
        return 0
    total = 0
    for candidate in _safe_list(agent1a.get("action_gap_candidates")):
        if isinstance(candidate, dict):
            total += _count_list(candidate.get("known_conditions"))
    return total


def _count_agent1a_context_refs(agent1a: Any) -> int:
    if not isinstance(agent1a, dict):
        return 0
    refs = []
    for candidate in _safe_list(agent1a.get("action_gap_candidates")):
        if isinstance(candidate, dict):
            refs.extend(_safe_list(candidate.get("context_refs")))
    for alignment in _safe_list(agent1a.get("action_context_alignment")):
        if isinstance(alignment, dict) and alignment.get("context_ref"):
            refs.append(alignment["context_ref"])
    return len(set(refs))


def _count_nested_list_items(items: List[Any], field: str) -> int:
    total = 0
    for item in items:
        if isinstance(item, dict):
            total += _count_list(item.get(field))
    return total


def _build_summary(output_root: Path, run_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "output_root": str(output_root),
        "purpose": "Context View value baseline for Text vs Structured vs Human Compiler Context.",
        "versions": {
            "A_text_only": "Current requirement only; no Context.",
            "B_structured_context": "Manual Context Package V2 runtime input.",
            "C_compiler_context": "Human Context Markdown compiled into Context Package V2.",
        },
        "run_records": run_records,
        "metrics": {},
    }

    for case_id in CASES:
        summary["metrics"][case_id] = {}
        for version_id in VERSIONS:
            version_dir = output_root / case_id / version_id
            summary["metrics"][case_id][version_id] = _summarize_result(version_dir)

    (output_root / "summary_metrics.json").write_text(
        _json_dump(summary),
        encoding="utf-8",
    )
    (output_root / "summary.md").write_text(
        _render_summary_markdown(summary),
        encoding="utf-8",
    )
    return summary


def _render_summary_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Context Comparison Baseline Summary",
        "",
        f"- output_root: `{summary['output_root']}`",
        f"- generated_at: `{summary['generated_at']}`",
        "",
        "## Metrics",
        "",
        "| Case | Version | Status | A1A specific unknowns | A1A unassigned unknowns | A1A context refs | A1B questions | risk_items | risk context_refs | Agent3 output count |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for case_id, versions in summary["metrics"].items():
        for version_id, metrics in versions.items():
            agent3_total = sum(metrics.get("agent3_output_counts", {}).values())
            lines.append(
                "| "
                f"{case_id} | {version_id} | {metrics.get('status')} | "
                f"{metrics.get('specific_unknown_count', 0)} | "
                f"{metrics.get('unassigned_unknown_count', 0)} | "
                f"{metrics.get('agent1a_context_ref_count', 0)} | "
                f"{metrics.get('agent1b_question_count', 0)} | "
                f"{metrics.get('risk_item_count', 0)} | "
                f"{metrics.get('risk_items_context_ref_count', 0)} | "
                f"{agent3_total} |"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `unknown_type_counts` is heuristic and only supports trend comparison.",
            "- This baseline evaluates information flow, not model quality scoring.",
            "- The production workflow is not modified by this script.",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_cases(selected_cases: Optional[List[str]]) -> List[str]:
    if not selected_cases:
        return list(CASES.keys())
    unknown = [case_id for case_id in selected_cases if case_id not in CASES]
    if unknown:
        raise ValueError(f"Unknown case id: {', '.join(unknown)}")
    return selected_cases


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Context View comparison baseline cases."
    )
    parser.add_argument(
        "--agent-mode",
        choices=["real", "fake"],
        default="real",
        help="Pass-through Agent mode for verify_workflow.py.",
    )
    parser.add_argument(
        "--output-root",
        help=(
            "Output root. Defaults to outputs/context_comparison_runs/"
            "context_comparison_{timestamp}."
        ),
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=list(CASES.keys()),
        help="Run only the selected case. Can be provided multiple times.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Do not call verify_workflow.py; only summarize an existing output root.",
    )
    args = parser.parse_args()

    if args.output_root:
        output_root = Path(args.output_root)
        if not output_root.is_absolute():
            output_root = PROJECT_ROOT / output_root
    else:
        if args.skip_run:
            raise SystemExit("--output-root is required when --skip-run is used.")
        output_root = (
            PROJECT_ROOT
            / "outputs"
            / "context_comparison_runs"
            / f"context_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    selected_cases = _resolve_cases(args.case)
    run_records: List[Dict[str, Any]] = []

    if not args.skip_run:
        compiled_paths = _compile_human_contexts(output_root)
        for case_id in selected_cases:
            for version_id in VERSIONS:
                print(f"running {case_id} {version_id} ({args.agent_mode})")
                record = _run_verify(
                    case_id=case_id,
                    version_id=version_id,
                    case_config=CASES[case_id],
                    compiled_paths=compiled_paths,
                    agent_mode=args.agent_mode,
                    version_output_dir=output_root / case_id / version_id,
                )
                run_records.append(record)
                print(f"  exit_code={record['exit_code']}")

    summary = _build_summary(output_root, run_records)
    print(f"summary_metrics: {output_root / 'summary_metrics.json'}")
    print(f"summary_markdown: {output_root / 'summary.md'}")
    print("cases:")
    for case_id in selected_cases:
        case_metrics = summary["metrics"].get(case_id, {})
        print(f"  - {case_id}: {', '.join(case_metrics.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
