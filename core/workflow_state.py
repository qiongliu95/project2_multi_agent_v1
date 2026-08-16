"""
Minimal Workflow State helpers.

Workflow State records one pipeline run's outer execution state. It does not
replace Agent business output, validate results, route stages, or call tools.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


STAGE_PENDING = "pending"
STAGE_RUNNING = "running"
STAGE_SUCCESS = "success"
STAGE_FAILED = "failed"
STAGE_SKIPPED = "skipped"

WORKFLOW_PENDING = "pending"
WORKFLOW_RUNNING = "running"
WORKFLOW_COMPLETED = "completed"
WORKFLOW_FAILED = "failed"
WORKFLOW_STOPPED = "stopped"


def _build_stage_state(
    status: str = STAGE_PENDING,
    output: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "output": output,
        "error": error,
    }


def create_workflow_state(
    *,
    run_id: str,
    requirement_text: str,
    stage_order: List[str],
    context_sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create the outer state for one pipeline execution.
    """
    return {
        "run_id": run_id,
        "input": {
            "requirement_text": requirement_text,
            "context_sources": context_sources or [],
        },
        "context": {
            "items": [],
        },
        "stages": {
            stage_id: _build_stage_state()
            for stage_id in stage_order
        },
        "control": {
            "current_stage": None,
            "status": WORKFLOW_PENDING,
            "stop_reason": None,
            "human_review_required": False,
        },
        "errors": [],
    }


def start_workflow(state: Dict[str, Any]) -> None:
    state["control"]["status"] = WORKFLOW_RUNNING


def complete_workflow(state: Dict[str, Any]) -> None:
    state["control"]["status"] = WORKFLOW_COMPLETED
    state["control"]["current_stage"] = None


def stop_workflow(state: Dict[str, Any], reason: str) -> None:
    state["control"]["status"] = WORKFLOW_STOPPED
    state["control"]["stop_reason"] = reason
    state["control"]["current_stage"] = None


def start_stage(state: Dict[str, Any], stage_id: str) -> None:
    state["control"]["current_stage"] = stage_id
    state["stages"][stage_id]["status"] = STAGE_RUNNING
    state["stages"][stage_id]["error"] = None


def complete_stage(
    state: Dict[str, Any],
    stage_id: str,
    output: Dict[str, Any],
) -> None:
    state["stages"][stage_id]["status"] = STAGE_SUCCESS
    state["stages"][stage_id]["output"] = output
    state["stages"][stage_id]["error"] = None


def build_error_record(
    *,
    stage_id: str,
    error: Exception,
) -> Dict[str, str]:
    return {
        "stage_id": stage_id,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def fail_stage(
    state: Dict[str, Any],
    stage_id: str,
    error: Exception,
) -> Dict[str, str]:
    error_record = build_error_record(stage_id=stage_id, error=error)
    state["stages"][stage_id]["status"] = STAGE_FAILED
    state["stages"][stage_id]["error"] = error_record
    state["errors"].append(error_record)
    state["control"]["status"] = WORKFLOW_FAILED
    state["control"]["stop_reason"] = f"{stage_id} failed"
    state["control"]["current_stage"] = stage_id
    return error_record


def skip_pending_stages(
    state: Dict[str, Any],
    stage_order: List[str],
) -> None:
    for stage_id in stage_order:
        if state["stages"][stage_id]["status"] == STAGE_PENDING:
            state["stages"][stage_id]["status"] = STAGE_SKIPPED


def mark_human_review_required(
    state: Dict[str, Any],
    required: bool,
) -> None:
    if required:
        state["control"]["human_review_required"] = True


def add_error_record(
    state: Dict[str, Any],
    error_record: Dict[str, Any],
) -> None:
    state["errors"].append(error_record)


def add_context_item(
    state: Dict[str, Any],
    context_item: Dict[str, Any],
) -> None:
    state["context"]["items"].append(context_item)


def add_context_error(
    state: Dict[str, Any],
    *,
    source: Dict[str, Any],
    error: Exception,
) -> Dict[str, Any]:
    source_id = source.get("source_id") or source.get("id") or "context_source"
    error_record = {
        "stage_id": f"context:{source_id}",
        "error_type": type(error).__name__,
        "message": str(error),
    }
    failed_item = {
        "context_id": source_id,
        "source": source,
        "content_type": source.get("type"),
        "content": None,
        "status": "failed",
        "error": error_record,
    }
    state["context"]["items"].append(failed_item)
    state["errors"].append(error_record)
    return failed_item
