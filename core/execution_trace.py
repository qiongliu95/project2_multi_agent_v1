"""
Execution Trace utilities.

This module records Agent execution as a side effect only. It does not validate,
route, retry, or change any Agent input/output.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRACE_ROOT = PROJECT_ROOT / "outputs" / "traces"
DEFAULT_REGISTRY_REF_PATH = PROJECT_ROOT / "configs" / "agent_registry_refs.json"


def load_registry_refs(
    registry_ref_path: str | Path = DEFAULT_REGISTRY_REF_PATH,
) -> Dict[str, Any]:
    """
    Load the minimal Agent Registry reference mapping used by trace records.
    """
    path = Path(registry_ref_path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_registry_ref(
    agent_id: str,
    registry_refs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a compact registry reference for one Agent.
    """
    registry_version = registry_refs.get("registry_version", "v2")
    agent_ref = registry_refs.get("agents", {}).get(agent_id, {})

    return {
        "registry_version": registry_version,
        "agent_id": agent_id,
        "stage": agent_ref.get("stage"),
        "schema_name": agent_ref.get("schema_name"),
        "prompt_ref": agent_ref.get("prompt_ref"),
        "implementation_ref": agent_ref.get("implementation_ref"),
    }


def build_agent_trace(
    *,
    run_id: str,
    case_id: str,
    agent_id: str,
    stage: str,
    input_sources: List[str],
    output_snapshot: Dict[str, Any],
    registry_ref: Optional[Dict[str, Any]] = None,
    execution_status: str = "completed",
    human_review_required: bool = False,
    human_review_reasons: Optional[List[str]] = None,
    original_requirement_ref: Optional[str] = None,
    context_view: Optional[Dict[str, Any]] = None,
    context_consumption: Optional[List[Dict[str, Any]]] = None,
    final_input_sources: Optional[List[str]] = None,
    information_flow_audit: Optional[Dict[str, Any]] = None,
    source_summary: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build one Agent execution trace record.

    The trace stores what happened after an Agent finished. It intentionally
    does not inspect whether the Agent output is correct.
    """
    timestamp = datetime.now().isoformat()

    trace = {
        "trace_id": f"{run_id}_{case_id}_{agent_id}",
        "run_id": run_id,
        "case_id": case_id,
        "agent_id": agent_id,
        "stage": stage,
        "registry_ref": registry_ref
        or {
            "registry_version": "v2",
            "agent_id": agent_id,
        },
        "input_sources": input_sources,
        "output_snapshot": output_snapshot,
        "execution_status": execution_status,
        "human_review": {
            "required": human_review_required,
            "reasons": human_review_reasons or [],
        },
        "recorded_at": timestamp,
    }

    if original_requirement_ref is not None:
        trace["original_requirement_ref"] = original_requirement_ref
    if context_view is not None:
        trace["context_view"] = context_view
    if context_consumption is not None:
        trace["context_consumption"] = context_consumption
    if final_input_sources is not None:
        trace["final_input_sources"] = final_input_sources
    if information_flow_audit is not None:
        trace["information_flow_audit"] = information_flow_audit
    if source_summary is not None:
        trace["source_summary"] = source_summary

    return trace


def append_agent_trace(
    trace: Dict[str, Any],
    trace_root: str | Path = DEFAULT_TRACE_ROOT,
) -> Path:
    """
    Append one Agent execution trace to outputs/traces/{run_id}/agent_traces.jsonl.
    """
    run_id = trace["run_id"]
    trace_dir = Path(trace_root) / run_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    trace_path = trace_dir / "agent_traces.jsonl"
    with trace_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(trace, ensure_ascii=False) + "\n")

    return trace_path


def build_tool_trace(
    *,
    run_id: str,
    case_id: str,
    tool_id: str,
    input_refs: List[str],
    capability_type: str = "tool",
    output_ref: Optional[str] = None,
    output_snapshot: Optional[Dict[str, Any]] = None,
    execution_status: str = "completed",
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build one Tool execution trace record.
    """
    timestamp = datetime.now().isoformat()

    return {
        "trace_id": f"{run_id}_{case_id}_{tool_id}_{timestamp}",
        "run_id": run_id,
        "case_id": case_id,
        "tool_id": tool_id,
        "capability_type": capability_type,
        "input_refs": input_refs,
        "output_ref": output_ref,
        "output_snapshot": output_snapshot or {},
        "execution_status": execution_status,
        "error": error,
        "recorded_at": timestamp,
    }


def append_tool_trace(
    trace: Dict[str, Any],
    trace_root: str | Path = DEFAULT_TRACE_ROOT,
) -> Path:
    """
    Append one Tool execution trace to outputs/traces/{run_id}/tool_traces.jsonl.
    """
    run_id = trace["run_id"]
    trace_dir = Path(trace_root) / run_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    trace_path = trace_dir / "tool_traces.jsonl"
    with trace_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(trace, ensure_ascii=False) + "\n")

    return trace_path


def build_trace_event(
    *,
    event_type: str,
    trace: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build one unified event record for reconstructing real call order.

    Agent and Tool specific trace files remain as compatibility views. The
    unified event log is the preferred ordered stream for one run.
    """
    event_name = trace.get("agent_id") or trace.get("tool_id")
    input_refs = trace.get("input_sources") or trace.get("input_refs") or []
    capability_type = trace.get("capability_type") or event_type

    return {
        "event_id": trace.get("trace_id"),
        "event_type": event_type,
        "capability_type": capability_type,
        "run_id": trace.get("run_id"),
        "case_id": trace.get("case_id"),
        "name": event_name,
        "stage": trace.get("stage"),
        "input_refs": input_refs,
        "output_ref": trace.get("output_ref"),
        "output_snapshot": trace.get("output_snapshot", {}),
        "execution_status": trace.get("execution_status"),
        "human_review": trace.get("human_review"),
        "error": trace.get("error"),
        "recorded_at": trace.get("recorded_at"),
        "payload": trace,
    }


def append_trace_event(
    event: Dict[str, Any],
    trace_root: str | Path = DEFAULT_TRACE_ROOT,
) -> Path:
    """
    Append one ordered Workflow event to outputs/traces/{run_id}/workflow_events.jsonl.
    """
    run_id = event["run_id"]
    trace_dir = Path(trace_root) / run_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    trace_path = trace_dir / "workflow_events.jsonl"
    with trace_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

    return trace_path
