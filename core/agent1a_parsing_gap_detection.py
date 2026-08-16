"""
Agent1A：需求解析 + 动作缺口识别。

作用：
- 读取 Agent1A prompt
- 基于 requirement_text 调用大模型
- 解析并返回结构化结果
- 输出 parsing 结果和 action_gap_candidates

主要流程：
1. 读取 prompts/agent1a_parsing_gap_detection.md
2. 组装输入 payload
3. 调用统一 LLM 封装
4. 解析 JSON
5. 对输出字段做最小兜底修正

设计考虑：
- 该模块只负责“提取 + 缺口识别”，不负责生成 open_questions
- 如果模型输出字段缺失，做最小补齐，避免影响后续 pipeline
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.llm_client import call_llm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "agent1a_parsing_gap_detection.md"


def load_prompt(prompt_path: str | Path) -> str:
    """
    读取 prompt 文件内容。

    输入：
    - prompt_path: prompt 文件路径

    输出：
    - prompt 文本
    """
    path = Path(prompt_path)
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def build_payload(requirement_text: str) -> Dict[str, Any]:
    """
    构造发送给模型的输入 payload。

    输入：
    - requirement_text: 原始需求文本

    输出：
    - payload 字典
    """
    return {"requirement_text": requirement_text}


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    """
    解析模型返回的 JSON 文本。

    输入：
    - raw_text: 模型原始输出

    输出：
    - 解析后的字典
    """
    text = raw_text.strip()

    # 兼容模型偶发输出 markdown code fence 的情况
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return json.loads(text)


def _normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    normalized_items: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized_items.append(text)
    return normalized_items


def normalize_action_gap_candidates(
    action_gap_candidates: Any,
    main_flow: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    规范 action_gap_candidates 字段，确保结构可供后续使用。

    输入：
    - action_gap_candidates: 模型输出的原始候选项
    - main_flow: 已解析出的动作列表

    输出：
    - 规范化后的 action_gap_candidates 列表
    """
    normalized_candidates: List[Dict[str, Any]] = []
    contract_warnings: List[Dict[str, Any]] = []
    allowed_gap_types = {"flow", "rule", "scope", "input_output", ""}

    if not isinstance(action_gap_candidates, list):
        action_gap_candidates = []

    # 先吸收模型输出中格式合法的项
    for item in action_gap_candidates:
        if not isinstance(item, dict):
            continue

        action = str(item.get("action", "")).strip()
        has_gap = bool(item.get("has_gap", False))
        gap_type = str(item.get("gap_type", "")).strip()

        if gap_type not in allowed_gap_types:
            gap_type = ""

        if not action:
            continue

        specific_unknowns = _normalize_string_list(
            item.get("specific_unknowns", [])
        )
        context_refs = _normalize_string_list(item.get("context_refs", []))

        if has_gap and not specific_unknowns and not context_refs:
            contract_warnings.append(
                {
                    "warning_type": "invalid_empty_gap",
                    "action": action,
                    "original_gap_type": gap_type,
                    "message": (
                        "Agent1A returned has_gap=true without "
                        "specific_unknowns or context_refs; normalized to no gap."
                    ),
                }
            )
            has_gap = False
            gap_type = ""

        normalized_candidates.append(
            {
                "action": action,
                "has_gap": has_gap,
                "gap_type": gap_type,
                "known_conditions": _normalize_string_list(
                    item.get("known_conditions", [])
                ),
                "specific_unknowns": specific_unknowns,
                "context_refs": context_refs,
            }
        )

    # 再基于 main_flow 补齐缺失动作，避免后续阶段无法覆盖全部动作
    existing_actions = {item["action"] for item in normalized_candidates}
    for action in main_flow:
        if action not in existing_actions:
            normalized_candidates.append(
                {
                    "action": action,
                    "has_gap": False,
                    "gap_type": "",
                    "known_conditions": [],
                    "specific_unknowns": [],
                    "context_refs": [],
                }
            )

    return normalized_candidates, contract_warnings


def normalize_context_unknown_assessments(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    allowed_statuses = {
        "fully_resolved",
        "partially_resolved",
        "unresolved",
        "unassigned",
    }
    normalized_items: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        context_ref = str(item.get("context_ref", "")).strip()
        if not context_ref:
            continue
        resolution_status = str(item.get("resolution_status", "")).strip()
        if resolution_status not in allowed_statuses:
            resolution_status = "unresolved"
        normalized_items.append(
            {
                "context_ref": context_ref,
                "resolution_status": resolution_status,
                "remaining_unknowns": _normalize_string_list(
                    item.get("remaining_unknowns", [])
                ),
                "reason": str(item.get("reason", "")).strip(),
            }
        )

    return normalized_items


def normalize_output(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    对 Agent1A 输出做最小兜底修正。

    输入：
    - result: 模型解析结果

    输出：
    - 规范化后的结果字典
    """
    functional_goal = str(result.get("functional_goal", "")).strip()

    user_roles = result.get("user_roles", [])
    if not isinstance(user_roles, list):
        user_roles = []

    main_flow = result.get("main_flow", [])
    if not isinstance(main_flow, list):
        main_flow = []

    preconditions = result.get("preconditions", [])
    if not isinstance(preconditions, list):
        preconditions = []

    edge_cases = result.get("edge_cases", [])
    if not isinstance(edge_cases, list):
        edge_cases = []

    alternative_flows = result.get("alternative_flows", [])
    if not isinstance(alternative_flows, list):
        alternative_flows = []

    action_gap_candidates, contract_warnings = normalize_action_gap_candidates(
        action_gap_candidates=result.get("action_gap_candidates", []),
        main_flow=main_flow,
    )

    context_unknown_assessments = normalize_context_unknown_assessments(
        result.get("context_unknown_assessments", [])
    )

    return {
        "functional_goal": functional_goal,
        "user_roles": user_roles,
        "main_flow": main_flow,
        "alternative_flows": _normalize_string_list(alternative_flows),
        "preconditions": preconditions,
        "edge_cases": edge_cases,
        "action_gap_candidates": action_gap_candidates,
        "context_unknown_assessments": context_unknown_assessments,
        "contract_warnings": contract_warnings,
    }


def run_agent1a_parsing_gap_detection(requirement_text: str) -> Dict[str, Any]:
    """
    执行 Agent1A：需求解析 + 动作缺口识别。

    输入：
    - requirement_text: 原始需求文本

    输出：
    - Agent1A 的结构化结果
    """
    # 读取 prompt 并构造输入
    prompt = load_prompt(PROMPT_PATH)
    payload = build_payload(requirement_text)

    # 调用模型并解析输出
    raw_response = call_llm(prompt=prompt, payload=payload)
    parsed_result = parse_json_response(raw_response)

    # 规范化结果，保证后续 Agent1B 可消费
    return normalize_output(parsed_result)
