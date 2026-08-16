"""
Pipeline 执行器。

作用：
- 按固定顺序执行主链路 Agent
- baseline 下使用 Agent1A + Agent1B 两阶段结构
- 可选保留旧的 Agent1 Two-Stage 扩展能力
- 返回标准化结果
- 记录最小 Workflow State 和 Execution Trace

主要流程：
1. 执行 Agent1A：需求解析 + 动作缺口识别
2. 执行 Agent1B：基于缺口生成 open_questions
3. 执行 Agent2：风险分析
4. 执行 Agent3：测试设计
5. 执行 Agent4：汇总输出

设计考虑：
- 旧 Agent1 冻结保留，不再作为默认主链路
- baseline 主链路升级为“两阶段：缺口识别 → 问题生成”
- Agent2 / Agent3 / Agent4 的输入结构保持兼容，降低改动范围
- 旧的 Agent1 Two-Stage 扩展仅作为历史/兼容能力保留
- Workflow State 只记录外围执行状态，不替代 Agent 业务输出
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.agent1a_parsing_gap_detection import run_agent1a_parsing_gap_detection
from core.agent1b_question_generation import run_agent1b_question_generation
from core.agent2_risk_analysis import run_agent2_risk
from core.agent3_test_design import run_agent3_test
from core.agent4_result_summary import run_agent4_summary
from core.context_tools import (
    align_action_gap_candidates_with_context,
    build_agent_context_view,
    build_context_augmented_requirement,
    build_context_consumption,
    build_context_source_summary,
    build_final_input_sources,
    build_legacy_context_fidelity_audit,
    build_rendered_agent_input,
    load_context_source,
)
from core.execution_trace import (
    append_agent_trace,
    append_trace_event,
    append_tool_trace,
    build_agent_trace,
    build_trace_event,
    build_tool_trace,
    get_registry_ref,
    load_registry_refs,
)
from core.workflow_state import (
    add_context_item,
    add_error_record,
    complete_stage,
    complete_workflow,
    create_workflow_state,
    fail_stage,
    mark_human_review_required,
    skip_pending_stages,
    start_stage,
    start_workflow,
    stop_workflow,
)


STAGE_ORDER = [
    "agent1a",
    "agent1b",
    "agent2",
    "agent3",
    "agent4",
]


def _human_review_state(
    agent_id: str,
    output_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Record lightweight human-review state without changing workflow behavior.
    """
    reasons = []

    if agent_id == "clarification" and output_snapshot.get("open_questions"):
        reasons.append("open_questions 非空")

    if agent_id == "risk_analysis" and output_snapshot.get("missing_info"):
        reasons.append("missing_info 非空")

    if agent_id == "controlled_test_draft":
        drafts = output_snapshot.get("test_case_drafts", [])
        if any("信息不足" in str(item) for item in drafts):
            reasons.append("test_case_drafts 表示信息不足")

    if agent_id == "review" and output_snapshot.get("human_review_required"):
        reasons.append("review 输出 human_review_required=true")

    return {
        "required": bool(reasons),
        "reasons": reasons,
    }


def _record_agent_trace(
    *,
    run_id: str,
    case_id: str,
    agent_id: str,
    stage: str,
    input_sources: List[str],
    output_snapshot: Dict[str, Any],
    registry_refs: Dict[str, Any],
    execution_status: str = "completed",
    original_requirement_ref: str | None = None,
    context_view: Dict[str, Any] | None = None,
    context_consumption: List[Dict[str, Any]] | None = None,
    final_input_sources: List[str] | None = None,
    information_flow_audit: Dict[str, Any] | None = None,
    source_summary: List[Dict[str, Any]] | None = None,
) -> None:
    """
    Append an Agent trace record as a side effect only.
    """
    try:
        human_review = _human_review_state(
            agent_id=agent_id,
            output_snapshot=output_snapshot,
        )
        trace = build_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id=agent_id,
            stage=stage,
            input_sources=input_sources,
            output_snapshot=output_snapshot,
            registry_ref=get_registry_ref(agent_id, registry_refs),
            execution_status=execution_status,
            human_review_required=human_review["required"],
            human_review_reasons=human_review["reasons"],
            original_requirement_ref=original_requirement_ref,
            context_view=context_view,
            context_consumption=context_consumption,
            final_input_sources=final_input_sources,
            information_flow_audit=information_flow_audit,
            source_summary=source_summary,
        )
        append_agent_trace(trace)
        append_trace_event(
            build_trace_event(
                event_type="agent",
                trace=trace,
            )
        )
    except Exception as error:
        print(f"Trace 记录失败，不影响主流程：{error}")


def _record_tool_trace(
    *,
    run_id: str,
    case_id: str,
    tool_id: str,
    input_refs: List[str],
    capability_type: str = "tool",
    output_ref: str | None = None,
    output_snapshot: Dict[str, Any] | None = None,
    execution_status: str = "completed",
    error: Dict[str, Any] | None = None,
) -> None:
    """
    Append a Tool trace record as a side effect only.
    """
    try:
        trace = build_tool_trace(
            run_id=run_id,
            case_id=case_id,
            tool_id=tool_id,
            input_refs=input_refs,
            capability_type=capability_type,
            output_ref=output_ref,
            output_snapshot=output_snapshot,
            execution_status=execution_status,
            error=error,
        )
        append_tool_trace(trace)
        append_trace_event(
            build_trace_event(
                event_type=capability_type,
                trace=trace,
            )
        )
    except Exception as trace_error:
        print(f"Tool Trace 记录失败，不影响主流程：{trace_error}")


def _has_structured_context_v2(context_items: List[Dict[str, Any]]) -> bool:
    return any(
        item.get("status") == "success"
        and item.get("context_package_version") == "v2"
        and isinstance(item.get("structured_content"), dict)
        for item in context_items
    )


def _build_agent_input_context(
    *,
    agent_stage_id: str,
    requirement_text: str,
    context_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    context_view = build_agent_context_view(
        agent_id=agent_stage_id,
        context_items=context_items,
    )
    rendered_agent_input = build_rendered_agent_input(
        requirement_text=requirement_text,
        context_view=context_view,
    )
    context_consumption = build_context_consumption(context_view)
    final_input_sources = build_final_input_sources(context_view=context_view)
    return {
        "rendered_agent_input": rendered_agent_input,
        "context_view": context_view,
        "context_consumption": context_consumption,
        "final_input_sources": final_input_sources,
        "source_summary": build_context_source_summary(context_view),
    }


def _build_legacy_agent1a_input_context(
    *,
    requirement_text: str,
    context_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    rendered_agent_input = build_context_augmented_requirement(
        requirement_text=requirement_text,
        context_items=context_items,
    )
    final_input_sources = ["workflow_state.input.requirement_text"]
    if context_items:
        final_input_sources.append("workflow_state.context.items")
    return {
        "rendered_agent_input": rendered_agent_input,
        "context_view": {
            "agent_id": "agent1a",
            "context_package_version": None,
            "sections": {},
            "guidance": None,
        },
        "context_consumption": [],
        "final_input_sources": final_input_sources,
        "source_summary": [],
    }


def _build_plain_agent_input_context(
    *,
    agent_stage_id: str,
    requirement_text: str,
) -> Dict[str, Any]:
    return {
        "rendered_agent_input": requirement_text,
        "context_view": {
            "agent_id": agent_stage_id,
            "context_package_version": None,
            "sections": {},
            "guidance": None,
        },
        "context_consumption": [],
        "final_input_sources": ["workflow_state.input.requirement_text"],
        "source_summary": [],
    }


def _apply_human_review_state(
    *,
    workflow_state: Dict[str, Any],
    agent_id: str,
    output_snapshot: Dict[str, Any],
) -> None:
    human_review = _human_review_state(
        agent_id=agent_id,
        output_snapshot=output_snapshot,
    )
    mark_human_review_required(
        workflow_state,
        human_review["required"],
    )


def _build_final_output(
    *,
    case_id: str,
    requirement_text: str,
    agent1_parsing_result: Dict[str, Any] | None,
    agent1_questions_result: Dict[str, Any] | None,
    agent2_risk_result: Dict[str, Any] | None,
    agent3_test_result: Dict[str, Any] | None,
    agent4_summary_result: Dict[str, Any] | None,
) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "requirement_text": requirement_text,
        "agent_1_parsing": agent1_parsing_result,
        "agent_1_questions": agent1_questions_result,
        "agent_2_risk": agent2_risk_result,
        "agent_3_test": agent3_test_result,
        "agent_4_summary": agent4_summary_result,
    }


def _handle_agent_failure(
    *,
    workflow_state: Dict[str, Any],
    stage_id: str,
    error: Exception,
) -> None:
    fail_stage(
        workflow_state,
        stage_id,
        error,
    )
    skip_pending_stages(
        workflow_state,
        STAGE_ORDER,
    )


def _collect_context_sources(
    *,
    case: Dict[str, Any],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    context_sources = []
    context_sources.extend(config.get("context_sources", []))
    context_sources.extend(case.get("context_sources", []))
    return context_sources


def _load_context_sources(
    *,
    workflow_state: Dict[str, Any],
    context_sources: List[Dict[str, Any]],
    run_id: str,
    case_id: str,
) -> bool:
    for index, source in enumerate(context_sources):
        source_id = source.get("source_id") or source.get("id") or f"context_{index}"
        input_ref = f"context_sources[{index}]"
        context_item = load_context_source(source)
        add_context_item(workflow_state, context_item)
        capability_type = context_item.get("capability_type", "tool")
        capability_id = (
            context_item.get("tool_id")
            or context_item.get("skill_id")
            or "context_provider"
        )

        if context_item.get("status") == "failed" and context_item.get("error"):
            add_error_record(workflow_state, context_item["error"])

        _record_tool_trace(
            run_id=run_id,
            case_id=case_id,
            tool_id=capability_id,
            input_refs=[input_ref],
            capability_type=capability_type,
            output_ref=f"workflow_state.context.items.{source_id}",
            output_snapshot={
                "context_id": context_item.get("context_id"),
                "provider_id": context_item.get("provider_id"),
                "tool_id": context_item.get("tool_id"),
                "skill_id": context_item.get("skill_id"),
                "capability_type": capability_type,
                "required": context_item.get("required"),
                "status": context_item.get("status"),
                "context_package_version": context_item.get(
                    "context_package_version"
                ),
                "content_type": context_item.get("content_type"),
                "source": context_item.get("source"),
            },
            execution_status=(
                "failed" if context_item.get("status") == "failed" else "completed"
            ),
            error=context_item.get("error"),
        )

        if context_item.get("status") == "failed" and context_item.get("required"):
            stop_workflow(
                workflow_state,
                f"required context source failed: {source_id}",
            )
            skip_pending_stages(
                workflow_state,
                STAGE_ORDER,
            )
            return False

    return True


def run_pipeline_with_state(
    case: Dict[str, Any],
    config: Dict[str, Any],
    run_id: str = "manual_run",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    执行单条 Pipeline，并返回最终业务结果和 Workflow State。

    Workflow State 是外围运行状态，不改变五个 Agent 的输入、输出或执行顺序。
    """
    registry_refs = load_registry_refs()
    case_id = case["id"]
    requirement_text = case["requirement_text"]
    context_sources = _collect_context_sources(
        case=case,
        config=config,
    )
    workflow_state = create_workflow_state(
        run_id=run_id,
        requirement_text=requirement_text,
        stage_order=STAGE_ORDER,
        context_sources=context_sources,
    )
    start_workflow(workflow_state)

    agent1_parsing_result = None
    agent1_questions_result = None
    agent2_risk_result = None
    agent3_test_result = None
    agent4_summary_result = None

    should_continue = _load_context_sources(
        workflow_state=workflow_state,
        context_sources=context_sources,
        run_id=run_id,
        case_id=case_id,
    )
    if not should_continue:
        return (
            _build_final_output(
                case_id=case_id,
                requirement_text=requirement_text,
                agent1_parsing_result=agent1_parsing_result,
                agent1_questions_result=agent1_questions_result,
                agent2_risk_result=agent2_risk_result,
                agent3_test_result=agent3_test_result,
                agent4_summary_result=agent4_summary_result,
            ),
            workflow_state,
        )

    context_items = workflow_state["context"]["items"]
    has_structured_context_v2 = _has_structured_context_v2(context_items)
    if has_structured_context_v2:
        agent1a_input_context = _build_agent_input_context(
            agent_stage_id="agent1a",
            requirement_text=requirement_text,
            context_items=context_items,
        )
    else:
        agent1a_input_context = _build_legacy_agent1a_input_context(
            requirement_text=requirement_text,
            context_items=context_items,
        )

    # Step 1: Agent1A 需求解析 + 动作缺口识别
    try:
        start_stage(workflow_state, "agent1a")
        agent1_parsing_result = run_agent1a_parsing_gap_detection(
            requirement_text=agent1a_input_context["rendered_agent_input"]
        )
        if has_structured_context_v2:
            agent1_parsing_result = align_action_gap_candidates_with_context(
                agent1_result=agent1_parsing_result,
                context_items=context_items,
            )
        agent1a_information_flow_audit = None
        if context_items and not has_structured_context_v2:
            agent1a_information_flow_audit = build_legacy_context_fidelity_audit(
                context_items=context_items,
                agent1_result=agent1_parsing_result,
            )
        complete_stage(
            workflow_state,
            "agent1a",
            agent1_parsing_result,
        )
        _apply_human_review_state(
            workflow_state=workflow_state,
            agent_id="requirement_gap_detection",
            output_snapshot=agent1_parsing_result,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="requirement_gap_detection",
            stage="requirement_gap_detection",
            input_sources=agent1a_input_context["final_input_sources"],
            output_snapshot=agent1_parsing_result,
            registry_refs=registry_refs,
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent1a_input_context["context_view"],
            context_consumption=agent1a_input_context["context_consumption"],
            final_input_sources=agent1a_input_context["final_input_sources"],
            information_flow_audit=agent1a_information_flow_audit,
            source_summary=agent1a_input_context["source_summary"],
        )
    except Exception as error:
        _handle_agent_failure(
            workflow_state=workflow_state,
            stage_id="agent1a",
            error=error,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="requirement_gap_detection",
            stage="requirement_gap_detection",
            input_sources=agent1a_input_context["final_input_sources"],
            output_snapshot={},
            registry_refs=registry_refs,
            execution_status="failed",
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent1a_input_context["context_view"],
            context_consumption=agent1a_input_context["context_consumption"],
            final_input_sources=agent1a_input_context["final_input_sources"],
            source_summary=agent1a_input_context["source_summary"],
        )
        return (
            _build_final_output(
                case_id=case_id,
                requirement_text=requirement_text,
                agent1_parsing_result=agent1_parsing_result,
                agent1_questions_result=agent1_questions_result,
                agent2_risk_result=agent2_risk_result,
                agent3_test_result=agent3_test_result,
                agent4_summary_result=agent4_summary_result,
            ),
            workflow_state,
        )

    # Step 2: 生成 open_questions
    try:
        start_stage(workflow_state, "agent1b")
        if has_structured_context_v2:
            agent1b_input_context = _build_agent_input_context(
                agent_stage_id="agent1b",
                requirement_text=requirement_text,
                context_items=context_items,
            )
        else:
            agent1b_input_context = _build_plain_agent_input_context(
                agent_stage_id="agent1b",
                requirement_text=requirement_text,
            )
        if config.get("use_agent1_two_stage", False):
            from extensions.agent1_two_stage.agent1_question_decision import (
                run_agent1_question_decision,
            )

            agent1_questions_result = run_agent1_question_decision(
                requirement_text=agent1b_input_context["rendered_agent_input"],
                parsing_result=agent1_parsing_result,
            )
        else:
            agent1_questions_result = run_agent1b_question_generation(
                requirement_text=agent1b_input_context["rendered_agent_input"],
                main_flow=agent1_parsing_result.get("main_flow", []),
                action_gap_candidates=agent1_parsing_result.get(
                    "action_gap_candidates", []
                ),
                unassigned_unknowns=agent1_parsing_result.get(
                    "unassigned_unknowns", []
                ),
            )
        complete_stage(
            workflow_state,
            "agent1b",
            agent1_questions_result,
        )
        _apply_human_review_state(
            workflow_state=workflow_state,
            agent_id="clarification",
            output_snapshot=agent1_questions_result,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="clarification",
            stage="clarification",
            input_sources=[
                *agent1b_input_context["final_input_sources"],
                "agent_1_parsing.main_flow",
                "agent_1_parsing.action_gap_candidates",
            ],
            output_snapshot=agent1_questions_result,
            registry_refs=registry_refs,
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent1b_input_context["context_view"],
            context_consumption=agent1b_input_context["context_consumption"],
            final_input_sources=[
                *agent1b_input_context["final_input_sources"],
                "agent_1_parsing.main_flow",
                "agent_1_parsing.action_gap_candidates",
            ],
            source_summary=agent1b_input_context["source_summary"],
        )
    except Exception as error:
        _handle_agent_failure(
            workflow_state=workflow_state,
            stage_id="agent1b",
            error=error,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="clarification",
            stage="clarification",
            input_sources=[
                *agent1b_input_context["final_input_sources"],
                "agent_1_parsing.main_flow",
                "agent_1_parsing.action_gap_candidates",
            ],
            output_snapshot={},
            registry_refs=registry_refs,
            execution_status="failed",
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent1b_input_context["context_view"],
            context_consumption=agent1b_input_context["context_consumption"],
            final_input_sources=[
                *agent1b_input_context["final_input_sources"],
                "agent_1_parsing.main_flow",
                "agent_1_parsing.action_gap_candidates",
            ],
            source_summary=agent1b_input_context["source_summary"],
        )
        return (
            _build_final_output(
                case_id=case_id,
                requirement_text=requirement_text,
                agent1_parsing_result=agent1_parsing_result,
                agent1_questions_result=agent1_questions_result,
                agent2_risk_result=agent2_risk_result,
                agent3_test_result=agent3_test_result,
                agent4_summary_result=agent4_summary_result,
            ),
            workflow_state,
        )

    # Step 3: Agent2 风险分析
    try:
        start_stage(workflow_state, "agent2")
        if has_structured_context_v2:
            agent2_input_context = _build_agent_input_context(
                agent_stage_id="agent2",
                requirement_text=requirement_text,
                context_items=context_items,
            )
        else:
            agent2_input_context = _build_plain_agent_input_context(
                agent_stage_id="agent2",
                requirement_text=requirement_text,
            )
        agent2_risk_result = run_agent2_risk(
            requirement_text=agent2_input_context["rendered_agent_input"],
            parsing_result=agent1_parsing_result,
            question_result=agent1_questions_result,
        )
        complete_stage(
            workflow_state,
            "agent2",
            agent2_risk_result,
        )
        _apply_human_review_state(
            workflow_state=workflow_state,
            agent_id="risk_analysis",
            output_snapshot=agent2_risk_result,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="risk_analysis",
            stage="risk_analysis",
            input_sources=[
                *agent2_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
            ],
            output_snapshot=agent2_risk_result,
            registry_refs=registry_refs,
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent2_input_context["context_view"],
            context_consumption=agent2_input_context["context_consumption"],
            final_input_sources=[
                *agent2_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
            ],
            source_summary=agent2_input_context["source_summary"],
        )
    except Exception as error:
        _handle_agent_failure(
            workflow_state=workflow_state,
            stage_id="agent2",
            error=error,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="risk_analysis",
            stage="risk_analysis",
            input_sources=[
                *agent2_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
            ],
            output_snapshot={},
            registry_refs=registry_refs,
            execution_status="failed",
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent2_input_context["context_view"],
            context_consumption=agent2_input_context["context_consumption"],
            final_input_sources=[
                *agent2_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
            ],
            source_summary=agent2_input_context["source_summary"],
        )
        return (
            _build_final_output(
                case_id=case_id,
                requirement_text=requirement_text,
                agent1_parsing_result=agent1_parsing_result,
                agent1_questions_result=agent1_questions_result,
                agent2_risk_result=agent2_risk_result,
                agent3_test_result=agent3_test_result,
                agent4_summary_result=agent4_summary_result,
            ),
            workflow_state,
        )

    # Step 4: Agent3 测试设计
    try:
        start_stage(workflow_state, "agent3")
        if has_structured_context_v2:
            agent3_input_context = _build_agent_input_context(
                agent_stage_id="agent3",
                requirement_text=requirement_text,
                context_items=context_items,
            )
        else:
            agent3_input_context = _build_plain_agent_input_context(
                agent_stage_id="agent3",
                requirement_text=requirement_text,
            )
        agent3_test_result = run_agent3_test(
            requirement_text=agent3_input_context["rendered_agent_input"],
            parsing_result=agent1_parsing_result,
            strict_risks=agent2_risk_result,
        )
        complete_stage(
            workflow_state,
            "agent3",
            agent3_test_result,
        )
        _apply_human_review_state(
            workflow_state=workflow_state,
            agent_id="controlled_test_draft",
            output_snapshot=agent3_test_result,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="controlled_test_draft",
            stage="controlled_test_draft",
            input_sources=[
                *agent3_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_2_risk",
            ],
            output_snapshot=agent3_test_result,
            registry_refs=registry_refs,
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent3_input_context["context_view"],
            context_consumption=agent3_input_context["context_consumption"],
            final_input_sources=[
                *agent3_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_2_risk",
            ],
            source_summary=agent3_input_context["source_summary"],
        )
    except Exception as error:
        _handle_agent_failure(
            workflow_state=workflow_state,
            stage_id="agent3",
            error=error,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="controlled_test_draft",
            stage="controlled_test_draft",
            input_sources=[
                *agent3_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_2_risk",
            ],
            output_snapshot={},
            registry_refs=registry_refs,
            execution_status="failed",
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent3_input_context["context_view"],
            context_consumption=agent3_input_context["context_consumption"],
            final_input_sources=[
                *agent3_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_2_risk",
            ],
            source_summary=agent3_input_context["source_summary"],
        )
        return (
            _build_final_output(
                case_id=case_id,
                requirement_text=requirement_text,
                agent1_parsing_result=agent1_parsing_result,
                agent1_questions_result=agent1_questions_result,
                agent2_risk_result=agent2_risk_result,
                agent3_test_result=agent3_test_result,
                agent4_summary_result=agent4_summary_result,
            ),
            workflow_state,
        )

    # Step 5: Agent4 汇总结果
    try:
        start_stage(workflow_state, "agent4")
        if has_structured_context_v2:
            agent4_input_context = _build_agent_input_context(
                agent_stage_id="agent4",
                requirement_text=requirement_text,
                context_items=context_items,
            )
        else:
            agent4_input_context = _build_plain_agent_input_context(
                agent_stage_id="agent4",
                requirement_text=requirement_text,
            )
        agent4_summary_result = run_agent4_summary(
            requirement_text=agent4_input_context["rendered_agent_input"],
            parsing_result=agent1_parsing_result,
            strict_risks=agent2_risk_result,
            test_result=agent3_test_result,
            question_result=agent1_questions_result,
            full_risk_result=agent2_risk_result,
        )
        complete_stage(
            workflow_state,
            "agent4",
            agent4_summary_result,
        )
        _apply_human_review_state(
            workflow_state=workflow_state,
            agent_id="review",
            output_snapshot=agent4_summary_result,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="review",
            stage="review",
            input_sources=[
                *agent4_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
                "agent_2_risk",
                "agent_3_test",
            ],
            output_snapshot=agent4_summary_result,
            registry_refs=registry_refs,
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent4_input_context["context_view"],
            context_consumption=agent4_input_context["context_consumption"],
            final_input_sources=[
                *agent4_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
                "agent_2_risk",
                "agent_3_test",
            ],
            source_summary=agent4_input_context["source_summary"],
        )
    except Exception as error:
        _handle_agent_failure(
            workflow_state=workflow_state,
            stage_id="agent4",
            error=error,
        )
        _record_agent_trace(
            run_id=run_id,
            case_id=case_id,
            agent_id="review",
            stage="review",
            input_sources=[
                *agent4_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
                "agent_2_risk",
                "agent_3_test",
            ],
            output_snapshot={},
            registry_refs=registry_refs,
            execution_status="failed",
            original_requirement_ref="workflow_state.input.requirement_text",
            context_view=agent4_input_context["context_view"],
            context_consumption=agent4_input_context["context_consumption"],
            final_input_sources=[
                *agent4_input_context["final_input_sources"],
                "agent_1_parsing",
                "agent_1_questions",
                "agent_2_risk",
                "agent_3_test",
            ],
            source_summary=agent4_input_context["source_summary"],
        )
        return (
            _build_final_output(
                case_id=case_id,
                requirement_text=requirement_text,
                agent1_parsing_result=agent1_parsing_result,
                agent1_questions_result=agent1_questions_result,
                agent2_risk_result=agent2_risk_result,
                agent3_test_result=agent3_test_result,
                agent4_summary_result=agent4_summary_result,
            ),
            workflow_state,
        )

    complete_workflow(workflow_state)
    return (
        _build_final_output(
            case_id=case_id,
            requirement_text=requirement_text,
            agent1_parsing_result=agent1_parsing_result,
            agent1_questions_result=agent1_questions_result,
            agent2_risk_result=agent2_risk_result,
            agent3_test_result=agent3_test_result,
            agent4_summary_result=agent4_summary_result,
        ),
        workflow_state,
    )


def run_pipeline(
    case: Dict[str, Any],
    config: Dict[str, Any],
    run_id: str = "manual_run",
) -> Dict[str, Any]:
    """
    执行单条 Pipeline，并保持原有返回形态。
    """
    final_output, _workflow_state = run_pipeline_with_state(
        case=case,
        config=config,
        run_id=run_id,
    )
    return final_output
