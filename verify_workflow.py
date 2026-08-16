"""
Local workflow verification entry point.

This script runs one visible workflow case for manual observation. It reuses
the existing Pipeline, Workflow State, Context Package, and Trace files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_REQUIREMENT_TEXT = (
    "用户可以通过手机号注册账号，注册后可以登录系统，并支持查看和修改自己的个人资料，同时系统需记录用户操作日志。"
)
STAGE_OUTPUT_KEYS = [
    ("Agent1A", "agent_1_parsing"),
    ("Agent1B", "agent_1_questions"),
    ("Agent2", "agent_2_risk"),
    ("Agent3", "agent_3_test"),
    ("Agent4", "agent_4_summary"),
]


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


def _install_fake_agent_modules() -> None:
    def install(module_name: str, function_name: str, func: Any) -> None:
        module = types.ModuleType(module_name)
        setattr(module, function_name, func)
        sys.modules[module_name] = module

    def fake_agent1a(requirement_text: str) -> Dict[str, Any]:
        return {
            "__fake_agent_output__": True,
            "fake_mode_notice": "FAKE MODE: structure-only output, not an LLM result.",
            "functional_goal": "Observe Workflow structure with fake Agent1A output.",
            "user_roles": ["fake_user"],
            "main_flow": ["register", "login", "create_note", "edit_note", "delete_note"],
            "preconditions": [],
            "edge_cases": [],
            "action_gap_candidates": [
                {
                    "action": "delete_note",
                    "has_gap": True,
                    "gap_type": "rule",
                }
            ],
            "received_requirement_text_preview": requirement_text[:500],
        }

    def fake_agent1b(
        requirement_text: str,
        main_flow: List[str],
        action_gap_candidates: List[Dict[str, Any]],
        unassigned_unknowns: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        return {
            "__fake_agent_output__": True,
            "fake_mode_notice": "FAKE MODE: structure-only output, not an LLM result.",
            "open_questions": [
                "FAKE MODE: 删除笔记是否需要二次确认？",
                "FAKE MODE: 编辑笔记是否保留历史版本？",
            ],
        }

    def fake_agent2(
        requirement_text: str,
        parsing_result: Dict[str, Any],
        question_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "__fake_agent_output__": True,
            "fake_mode_notice": "FAKE MODE: structure-only output, not an LLM result.",
            "missing_info": ["delete confirmation rule", "edit version policy"],
            "risks": [
                {
                    "risk": "FAKE MODE: 删除规则不明确",
                    "evidence": "Agent1A action_gap_candidates",
                }
            ],
        }

    def fake_agent3(
        requirement_text: str,
        parsing_result: Dict[str, Any],
        strict_risks: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "__fake_agent_output__": True,
            "fake_mode_notice": "FAKE MODE: structure-only output, not an LLM result.",
            "test_case_drafts": [
                "FAKE MODE: 验证用户只能删除自己的笔记。",
                "FAKE MODE: 信息不足，删除二次确认规则待澄清。",
            ],
        }

    def fake_agent4(
        requirement_text: str,
        parsing_result: Dict[str, Any],
        strict_risks: Dict[str, Any],
        test_result: Dict[str, Any],
        question_result: Dict[str, Any],
        full_risk_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "__fake_agent_output__": True,
            "fake_mode_notice": "FAKE MODE: structure-only output, not an LLM result.",
            "summary": "FAKE MODE: Workflow completed with observable fake Agent outputs.",
            "human_review_required": True,
        }

    install(
        "core.agent1a_parsing_gap_detection",
        "run_agent1a_parsing_gap_detection",
        fake_agent1a,
    )
    install(
        "core.agent1b_question_generation",
        "run_agent1b_question_generation",
        fake_agent1b,
    )
    install("core.agent2_risk_analysis", "run_agent2_risk", fake_agent2)
    install("core.agent3_test_design", "run_agent3_test", fake_agent3)
    install("core.agent4_result_summary", "run_agent4_summary", fake_agent4)


def _ensure_markdown_context_file() -> Path:
    context_dir = PROJECT_ROOT / "outputs" / "verify_inputs"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_path = context_dir / "markdown_context.md"
    if not context_path.exists():
        context_path.write_text(
            "\n".join(
                [
                    "# Verification Markdown Context",
                    "",
                    "- Users own their notes.",
                    "- Deleting a note may require confirmation.",
                    "- Editing behavior may need version-history clarification.",
                ]
            ),
            encoding="utf-8",
        )
    return context_path


def _structured_context_file(path_override: str | None = None) -> Path:
    if path_override:
        path = Path(path_override)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path
    return PROJECT_ROOT / "data" / "context" / "registration_context_v2.json"


def _build_context_sources(
    mode: str,
    *,
    consumable_context: str | None = None,
    structured_context: str | None = None,
) -> List[Dict[str, Any]]:
    if mode == "text":
        return []
    if mode == "markdown":
        return [
            {
                "source_id": "verify_markdown_context",
                "type": "local_markdown",
                "path": str(_ensure_markdown_context_file()),
                "required": False,
            }
        ]
    if mode == "repository":
        return [
            {
                "source_id": "verify_repository_context",
                "type": "local_repository",
                "path": ".",
                "required": False,
            }
        ]
    if mode == "structured":
        return [
            {
                "type": "local_structured_context",
                "path": str(_structured_context_file(structured_context)),
                "required": False,
            }
        ]
    if mode == "auto-context":
        if not consumable_context:
            return []
        return [
            {
                "source_id": "auto_prepared_context",
                "type": "local_structured_context",
                "path": consumable_context,
                "required": True,
            }
        ]
    raise ValueError(f"Unsupported mode: {mode}")


def _load_base_config(context_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    config_path = PROJECT_ROOT / "configs" / "pipeline_config.json"
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    config["use_agent1_two_stage"] = False
    config["context_sources"] = context_sources
    return config


def _json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _content_summary(content: str | None, limit: int = 500) -> str:
    if not content:
        return ""
    compact = " ".join(content.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "... [truncated]"


def _print_header(title: str) -> None:
    print("")
    print("=" * 80)
    print(title)
    print("=" * 80)


def _print_context_summary(workflow_state: Dict[str, Any]) -> None:
    _print_header("Context Package")
    items = workflow_state.get("context", {}).get("items", [])
    if not items:
        print("No Context Package generated.")
        return

    for index, item in enumerate(items, start=1):
        print(f"[Context {index}]")
        print(f"  context_id: {item.get('context_id')}")
        print(f"  capability_type: {item.get('capability_type')}")
        print(f"  provider_id: {item.get('provider_id')}")
        print(f"  tool_id: {item.get('tool_id')}")
        print(f"  skill_id: {item.get('skill_id')}")
        print(f"  required: {item.get('required')}")
        print(f"  status: {item.get('status')}")
        if item.get("context_package_version"):
            print(f"  context_package_version: {item.get('context_package_version')}")
        if item.get("context_origin"):
            print(f"  context_origin: {item.get('context_origin')}")
        print(f"  content_type: {item.get('content_type')}")
        print(f"  content_length: {len(item.get('content') or '')}")
        if item.get("error"):
            print("  error:")
            print(_json_dump(item["error"]))

        source = item.get("source") or {}
        skill_metadata = source.get("skill_metadata")
        if skill_metadata:
            print("  skill_metadata:")
            print(_json_dump(skill_metadata))

        summary = _content_summary(item.get("content"))
        if summary:
            print("  content_summary:")
            print(f"  {summary}")

        structured_content = item.get("structured_content")
        if isinstance(structured_content, dict):
            print("  structured_content_summary:")
            for section, entries in structured_content.items():
                item_ids = [
                    entry.get("id")
                    for entry in entries
                    if isinstance(entry, dict) and entry.get("id")
                ]
                print(f"    - {section}: {len(item_ids)} items")
                if item_ids:
                    print(f"      ids: {', '.join(item_ids)}")


def _print_agent_context_details(agent_events: List[Dict[str, Any]]) -> None:
    _print_header("Agent Context Views")
    if not agent_events:
        print("No Agent Context View recorded.")
        return

    for event in agent_events:
        payload = event.get("payload") or {}
        print(f"\n[{event.get('name')}]")
        print(
            "  original_requirement_ref: "
            f"{payload.get('original_requirement_ref')}"
        )
        print("  final_input_sources:")
        for source in payload.get("final_input_sources") or event.get("input_refs") or []:
            print(f"    - {source}")

        context_consumption = payload.get("context_consumption") or []
        if context_consumption:
            print("  context_consumption:")
            for consumed in context_consumption:
                print(
                    "    - "
                    f"context_id={consumed.get('context_id')}, "
                    f"section={consumed.get('section')}, "
                    f"item_ids={', '.join(consumed.get('item_ids') or [])}"
                )
        else:
            print("  context_consumption: []")

        context_view = payload.get("context_view") or {}
        sections = context_view.get("sections") or {}
        if sections:
            print("  context_view:")
            if context_view.get("guidance"):
                print(f"    guidance: {context_view.get('guidance')}")
            for section, entries in sections.items():
                item_ids = [
                    entry.get("id")
                    for entry in entries
                    if isinstance(entry, dict) and entry.get("id")
                ]
                print(f"    - {section}: {', '.join(item_ids)}")
        else:
            print("  context_view: empty")

        source_summary = payload.get("source_summary") or []
        if source_summary:
            print("  source_summary:")
            for source in source_summary:
                print(
                    "    - "
                    f"{source.get('section')}.{source.get('item_id')} "
                    f"source_ref={source.get('source_ref')}"
                )

        information_flow_audit = payload.get("information_flow_audit")
        if isinstance(information_flow_audit, dict):
            print("  information_flow_audit:")
            for raw_source in information_flow_audit.get("raw_context_sources", []):
                print(
                    "    - raw_context "
                    f"context_id={raw_source.get('context_id')} "
                    f"source={raw_source.get('source')} "
                    f"content_length={raw_source.get('content_length')}"
                )
            extracted = information_flow_audit.get(
                "agent1a_extracted_action_gap_candidates", []
            )
            print(f"    extracted_action_gap_candidates: {len(extracted)}")


def _print_events(events: List[Dict[str, Any]]) -> None:
    _print_header("Tool / Skill Calls")
    capability_events = [
        event for event in events
        if event.get("event_type") in {"tool", "skill"}
    ]
    if not capability_events:
        print("No Tool or Skill event recorded.")
    for event in capability_events:
        print(
            f"- {event.get('event_type')} | "
            f"name={event.get('name')} | "
            f"status={event.get('execution_status')} | "
            f"output_ref={event.get('output_ref')}"
        )

    _print_header("Actual Agent Execution Order")
    agent_events = [
        event for event in events
        if event.get("event_type") == "agent"
    ]
    if not agent_events:
        print("No Agent event recorded.")
        return
    for index, event in enumerate(agent_events, start=1):
        print(
            f"{index}. {event.get('name')} "
            f"(stage={event.get('stage')}, status={event.get('execution_status')})"
        )
    _print_agent_context_details(agent_events)


def _print_stage_status(workflow_state: Dict[str, Any]) -> None:
    _print_header("Workflow State")
    control = workflow_state.get("control", {})
    print(f"current_stage: {control.get('current_stage')}")
    print(f"status: {control.get('status')}")
    print(f"stop_reason: {control.get('stop_reason')}")
    print(f"human_review_required: {control.get('human_review_required')}")

    _print_header("Stage Status")
    for stage_id, stage in workflow_state.get("stages", {}).items():
        print(f"- {stage_id}: {stage.get('status')}")
        if stage.get("error"):
            print(_json_dump(stage["error"]))


def _print_agent_outputs(final_output: Dict[str, Any]) -> None:
    _print_header("Agent Business Outputs")
    for display_name, output_key in STAGE_OUTPUT_KEYS:
        print(f"\n[{display_name}] {output_key}")
        print(_json_dump(final_output.get(output_key)))


def _save_observation_result(
    *,
    run_id: str,
    mode: str,
    agent_mode: str,
    final_output: Dict[str, Any],
    workflow_state: Dict[str, Any],
) -> Path:
    output_dir = PROJECT_ROOT / "outputs" / "verify_runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "result.json"
    output_path.write_text(
        _json_dump(
            {
                "run_id": run_id,
                "mode": mode,
                "agent_mode": agent_mode,
                "final_output": final_output,
                "workflow_state": workflow_state,
            }
        ),
        encoding="utf-8",
    )
    return output_path


def _print_output_paths(run_id: str, result_path: Path) -> None:
    trace_dir = PROJECT_ROOT / "outputs" / "traces" / run_id
    _print_header("Saved Files")
    print(f"result_json: {result_path}")
    print(f"trace_dir: {trace_dir}")
    print(f"workflow_events: {trace_dir / 'workflow_events.jsonl'}")
    print(f"agent_traces: {trace_dir / 'agent_traces.jsonl'}")
    print(f"tool_traces: {trace_dir / 'tool_traces.jsonl'}")


def _print_llm_client_info(agent_mode: str) -> None:
    if agent_mode != "real":
        return

    try:
        from core.llm_client import get_client_info

        _print_header("LLM Client")
        print(_json_dump(get_client_info()))
    except Exception as error:
        _print_header("LLM Client")
        print(f"Unable to load LLM client info: {type(error).__name__}: {error}")


def _import_pipeline(agent_mode: str) -> Any:
    if agent_mode == "fake":
        _install_fake_agent_modules()

    from core.pipeline_runner import run_pipeline_with_state

    return run_pipeline_with_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one local workflow verification case."
    )
    parser.add_argument(
        "--mode",
        choices=["text", "markdown", "repository", "structured", "auto-context"],
        required=True,
        help="Verification mode.",
    )
    parser.add_argument(
        "--agent-mode",
        choices=["real", "fake"],
        default="real",
        help="Use real Agents or clearly-labelled fake Agents for structure observation.",
    )
    parser.add_argument(
        "--requirement-text",
        default=DEFAULT_REQUIREMENT_TEXT,
        help="Requirement text to pass into the workflow.",
    )
    parser.add_argument(
        "--consumable-context",
        help=(
            "Reviewed consumable Context Package V2 path for "
            "--mode auto-context."
        ),
    )
    parser.add_argument(
        "--review-queue",
        help=(
            "Optional review queue path to print when --mode auto-context has "
            "no consumable context."
        ),
    )
    parser.add_argument(
        "--structured-context",
        help=(
            "Optional Context Package V2 JSON path for --mode structured. "
            "Useful for compiled human context comparison."
        ),
    )
    args = parser.parse_args()

    if args.mode == "auto-context" and not args.consumable_context:
        _print_header("Auto Context")
        print("No reviewed consumable Context Package V2 was provided.")
        print("Agent execution is intentionally stopped before the five-Agent workflow.")
        if args.review_queue:
            print(f"review_queue: {Path(args.review_queue)}")
        print("Build a consumable package after human review, then run:")
        print(
            "python verify_workflow.py --mode auto-context "
            "--consumable-context outputs/consumable_context/{run_id}.json "
            "--agent-mode fake"
        )
        return 0

    if args.agent_mode == "real" and not _has_api_config():
        print("真实 Agent 模式无法运行：未检测到 LLM_API_KEY 或 OPENAI_API_KEY。")
        print("请在 .env 或环境变量中配置 API Key 后重试。")
        print("如果只想观察 Workflow 结构，可以显式使用 fake 模式：")
        print(f"python verify_workflow.py --mode {args.mode} --agent-mode fake")
        return 2

    if args.agent_mode == "fake":
        print("FAKE AGENT MODE ENABLED")
        print("以下 Agent 输出仅用于观察 Workflow 结构，不是模型结果。")

    context_sources = _build_context_sources(
        args.mode,
        consumable_context=args.consumable_context,
        structured_context=args.structured_context,
    )
    config = _load_base_config(context_sources)
    case = {
        "id": f"verify_{args.mode}",
        "requirement_text": args.requirement_text,
    }
    run_id = (
        f"verify_{args.mode}_{args.agent_mode}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )

    _print_header("Input")
    print(f"run_id: {run_id}")
    print(f"mode: {args.mode}")
    print(f"agent_mode: {args.agent_mode}")
    print("requirement_text:")
    print(args.requirement_text)
    print("context_sources:")
    print(_json_dump(context_sources))
    _print_llm_client_info(args.agent_mode)

    try:
        run_pipeline_with_state = _import_pipeline(args.agent_mode)
        final_output, workflow_state = run_pipeline_with_state(
            case=case,
            config=config,
            run_id=run_id,
        )
    except Exception as error:
        print("")
        print("Workflow execution failed before a complete result was produced.")
        print(f"error_type: {type(error).__name__}")
        print(f"message: {error}")
        print("")
        print("如果这是 API、依赖或网络问题，可使用 fake 模式观察结构：")
        print(f"python verify_workflow.py --mode {args.mode} --agent-mode fake")
        return 1

    result_path = _save_observation_result(
        run_id=run_id,
        mode=args.mode,
        agent_mode=args.agent_mode,
        final_output=final_output,
        workflow_state=workflow_state,
    )
    events_path = PROJECT_ROOT / "outputs" / "traces" / run_id / "workflow_events.jsonl"
    events = _read_jsonl(events_path)

    _print_events(events)
    _print_context_summary(workflow_state)
    _print_stage_status(workflow_state)
    _print_agent_outputs(final_output)

    _print_header("Workflow Final")
    control = workflow_state.get("control", {})
    print(f"final_status: {control.get('status')}")
    print(f"stop_reason: {control.get('stop_reason')}")

    _print_output_paths(run_id, result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
