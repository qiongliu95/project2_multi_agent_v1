"""
Run requirement Markdown files through the existing five-Agent workflow.

This is the real-use entry point for product/test users: place one or more
Markdown requirement files in data/requirements_inbox and run this script.
Phase 1 intentionally runs text-only and does not attach Context sources.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "requirements_inbox"
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "requirement_runs"

STAGE_OUTPUTS = {
    "agent1a": "agent_1_parsing",
    "agent1b": "agent_1_questions",
    "agent2": "agent_2_risk",
    "agent3": "agent_3_test",
    "agent4": "agent_4_summary",
}


def _json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _safe_case_id(source_file: Path) -> str:
    stem = source_file.stem.strip().lower()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff_-]+", "_", stem)
    normalized = re.sub(r"_+", "_", normalized).strip("_-")
    return normalized or "requirement"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _load_dotenv_values(env_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _has_api_config() -> bool:
    dotenv_values = _load_dotenv_values(PROJECT_ROOT / ".env")
    return bool(
        os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or dotenv_values.get("LLM_API_KEY")
        or dotenv_values.get("OPENAI_API_KEY")
    )


def _load_base_config() -> Dict[str, Any]:
    config_path = PROJECT_ROOT / "configs" / "pipeline_config.json"
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    config["context_sources"] = []
    return config


def _install_fake_agents() -> None:
    # Reuse the existing fake Agent implementation used by verify_workflow.py.
    from verify_workflow import _install_fake_agent_modules

    _install_fake_agent_modules()


def _import_pipeline(agent_mode: str) -> Any:
    if agent_mode == "fake":
        _install_fake_agents()

    from core.pipeline_runner import run_pipeline_with_state

    return run_pipeline_with_state


def _discover_requirement_files(input_dir: Path) -> List[Path]:
    if not input_dir.exists():
        return []
    return sorted(
        path
        for path in input_dir.glob("*.md")
        if path.is_file() and not path.name.startswith(".")
    )


def _selected_requirement_files(args: argparse.Namespace) -> List[Path]:
    if args.file:
        source_file = _resolve_path(args.file)
        return [source_file]
    input_dir = _resolve_path(args.input_dir)
    return _discover_requirement_files(input_dir)


def _copy_trace_files(run_id: str, output_dir: Path) -> None:
    trace_dir = PROJECT_ROOT / "outputs" / "traces" / run_id
    if not trace_dir.exists():
        return

    for trace_name in [
        "workflow_events.jsonl",
        "agent_traces.jsonl",
        "tool_traces.jsonl",
    ]:
        source = trace_dir / trace_name
        if source.exists():
            shutil.copy2(source, output_dir / trace_name)


def _write_agent_outputs(final_output: Dict[str, Any], output_dir: Path) -> None:
    for file_prefix, output_key in STAGE_OUTPUTS.items():
        (output_dir / f"{file_prefix}_output.json").write_text(
            _json_dump(final_output.get(output_key)),
            encoding="utf-8",
        )


def _workflow_status(workflow_state: Dict[str, Any] | None) -> Tuple[str, Any]:
    if not workflow_state:
        return "failed_before_workflow_state", None
    control = workflow_state.get("control", {})
    return control.get("status", "unknown"), control.get("stop_reason")


def _write_final_result(
    *,
    output_dir: Path,
    run_id: str,
    case_id: str,
    source_file: Path,
    agent_mode: str,
    original_requirement_text: str,
    final_output: Dict[str, Any] | None,
    workflow_state: Dict[str, Any] | None,
    error: Dict[str, Any] | None = None,
) -> None:
    payload = {
        "run_id": run_id,
        "case_id": case_id,
        "source_file": _relative_or_absolute(source_file),
        "agent_mode": agent_mode,
        "original_requirement_text": original_requirement_text,
        "final_output": final_output,
        "workflow_state": workflow_state,
        "error": error,
    }
    (output_dir / "final_result.json").write_text(
        _json_dump(payload),
        encoding="utf-8",
    )


def _write_run_summary(
    *,
    output_dir: Path,
    run_id: str,
    case_id: str,
    source_file: Path,
    agent_mode: str,
    original_requirement_text: str,
    workflow_state: Dict[str, Any] | None,
    error: Dict[str, Any] | None = None,
) -> None:
    status, stop_reason = _workflow_status(workflow_state)
    lines = [
        "# Requirement Run Summary",
        "",
        f"- run_id: `{run_id}`",
        f"- case_id: `{case_id}`",
        f"- source_file: `{_relative_or_absolute(source_file)}`",
        f"- agent_mode: `{agent_mode}`",
        f"- workflow_status: `{status}`",
        f"- stop_reason: `{stop_reason}`",
        f"- original_requirement_text_length: `{len(original_requirement_text)}`",
        f"- context_sources: `[]`",
        "",
        "## Saved Files",
        "",
        "- `final_result.json`",
        "- `agent1a_output.json`",
        "- `agent1b_output.json`",
        "- `agent2_output.json`",
        "- `agent3_output.json`",
        "- `agent4_output.json`",
        "- `workflow_events.jsonl`",
        "- `agent_traces.jsonl`",
        "- `run_summary.md`",
    ]
    if error:
        lines.extend(
            [
                "",
                "## Error",
                "",
                f"- error_type: `{error.get('error_type')}`",
                f"- message: `{error.get('message')}`",
            ]
        )
    (output_dir / "run_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _empty_final_output(case_id: str, requirement_text: str) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "requirement_text": requirement_text,
        "agent_1_parsing": None,
        "agent_1_questions": None,
        "agent_2_risk": None,
        "agent_3_test": None,
        "agent_4_summary": None,
    }


def _run_one_requirement(
    *,
    source_file: Path,
    agent_mode: str,
    run_pipeline_with_state: Any,
) -> Dict[str, Any]:
    if source_file.suffix.lower() != ".md":
        raise ValueError(f"Requirement file must be Markdown: {source_file}")
    if not source_file.exists():
        raise FileNotFoundError(f"Requirement file not found: {source_file}")

    original_requirement_text = source_file.read_text(encoding="utf-8")
    if not original_requirement_text.strip():
        raise ValueError(f"Requirement file is empty: {source_file}")

    case_id = _safe_case_id(source_file)
    run_id = f"inbox_{case_id}_{agent_mode}_{_timestamp()}"
    output_dir = OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    case = {
        "id": case_id,
        "requirement_text": original_requirement_text,
    }
    config = _load_base_config()

    final_output: Dict[str, Any] | None = None
    workflow_state: Dict[str, Any] | None = None
    error_payload: Dict[str, Any] | None = None

    try:
        final_output, workflow_state = run_pipeline_with_state(
            case=case,
            config=config,
            run_id=run_id,
        )
    except Exception as error:
        error_payload = {
            "error_type": type(error).__name__,
            "message": str(error),
        }
        final_output = _empty_final_output(case_id, original_requirement_text)
        workflow_state = None

    _write_final_result(
        output_dir=output_dir,
        run_id=run_id,
        case_id=case_id,
        source_file=source_file,
        agent_mode=agent_mode,
        original_requirement_text=original_requirement_text,
        final_output=final_output,
        workflow_state=workflow_state,
        error=error_payload,
    )
    _write_agent_outputs(final_output or {}, output_dir)
    _copy_trace_files(run_id, output_dir)
    _write_run_summary(
        output_dir=output_dir,
        run_id=run_id,
        case_id=case_id,
        source_file=source_file,
        agent_mode=agent_mode,
        original_requirement_text=original_requirement_text,
        workflow_state=workflow_state,
        error=error_payload,
    )

    status, stop_reason = _workflow_status(workflow_state)
    if error_payload:
        status = "failed"
        stop_reason = error_payload["message"]

    return {
        "run_id": run_id,
        "case_id": case_id,
        "source_file": _relative_or_absolute(source_file),
        "output_dir": str(output_dir),
        "status": status,
        "stop_reason": stop_reason,
        "error": error_payload,
    }


def _run_requirements(files: Iterable[Path], agent_mode: str) -> List[Dict[str, Any]]:
    run_pipeline_with_state = _import_pipeline(agent_mode)
    results = []
    for source_file in files:
        print(f"running: {source_file}")
        try:
            result = _run_one_requirement(
                source_file=source_file,
                agent_mode=agent_mode,
                run_pipeline_with_state=run_pipeline_with_state,
            )
        except Exception as error:
            result = {
                "run_id": "",
                "case_id": _safe_case_id(source_file),
                "source_file": _relative_or_absolute(source_file),
                "output_dir": "",
                "status": "failed_before_run",
                "stop_reason": str(error),
                "error": {
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
            }
        results.append(result)
        print(f"  status={result['status']}")
        if result.get("output_dir"):
            print(f"  output_dir={result['output_dir']}")
    return results


def _print_results(results: List[Dict[str, Any]]) -> None:
    print("")
    print("Requirement inbox run summary")
    print("-" * 32)
    for result in results:
        print(f"- {result['source_file']}")
        print(f"  run_id: {result.get('run_id')}")
        print(f"  status: {result.get('status')}")
        print(f"  stop_reason: {result.get('stop_reason')}")
        print(f"  output_dir: {result.get('output_dir')}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Markdown requirement files through the existing workflow."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing Markdown requirement files.",
    )
    parser.add_argument(
        "--file",
        help="Run a single Markdown requirement file instead of scanning input-dir.",
    )
    parser.add_argument(
        "--agent-mode",
        choices=["real", "fake"],
        default="real",
        help="Use real Agents or clearly-labelled fake Agents.",
    )
    args = parser.parse_args()

    requirement_files = _selected_requirement_files(args)
    if not requirement_files:
        input_dir = _resolve_path(args.input_dir)
        print(f"No Markdown requirement files found in: {input_dir}")
        print("Place .md requirement files in data/requirements_inbox or use --file.")
        return 0

    if args.agent_mode == "real" and not _has_api_config():
        print("Real Agent mode cannot run: no LLM_API_KEY or OPENAI_API_KEY detected.")
        print("Use --agent-mode fake to observe workflow structure without model calls.")
        return 2

    if args.agent_mode == "fake":
        print("FAKE AGENT MODE ENABLED")
        print("Agent outputs are structure-only fake results, not model results.")

    results = _run_requirements(requirement_files, args.agent_mode)
    _print_results(results)
    return 1 if any(result["status"].startswith("failed") for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
