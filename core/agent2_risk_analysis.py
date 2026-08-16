"""
Agent2 风险分析模块。

作用：
- 基于需求与 Agent1 结果生成风险分析
- 返回 baseline 单通道风险输出

主要流程：
1. 读取 prompt
2. 组织输入
3. 调用模型
4. 解析 JSON

设计考虑：
- 当前 baseline 只输出单通道风险
- 双通道版本放在 extension 中
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from core.llm_client import call_llm


RISK_ARRAY_FIELDS = {
    "ambiguity_risks": "ambiguity",
    "edge_case_risks": "edge_case",
    "permission_risks": "permission",
    "data_risks": "data",
    "performance_risks": "performance",
}
LEGACY_RISK_FIELDS = [
    "ambiguity_risks",
    "missing_info",
    "edge_case_risks",
    "permission_risks",
    "data_risks",
    "performance_risks",
]


def load_prompt(prompt_path: str | Path) -> str:
    """
    读取 prompt 文件内容。

    输入：
    - prompt_path: 相对项目根目录的 prompt 路径

    输出：
    - prompt 文本
    """
    project_root = Path(__file__).resolve().parent.parent
    full_path = project_root / prompt_path
    return full_path.read_text(encoding="utf-8")


def parse_json_result(raw_text: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_text)
    except Exception:
        print("模型返回非标准JSON：")
        print(raw_text)
        raise


def _normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    normalized_items: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized_items.append(text)
    return normalized_items


def _normalize_match_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    replacements = [
        ("？", ""),
        ("?", ""),
        ("。", ""),
        ("，", ""),
        (",", ""),
        ("；", ""),
        (";", ""),
        (" ", ""),
        ("\n", ""),
        ("\t", ""),
        ("未确定", "未定义"),
        ("是什么", "未定义"),
        ("是否", ""),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _extract_context_items_from_rendered_input(
    requirement_text: str,
) -> Dict[str, Dict[str, str]]:
    """
    Extract Context View item ids from the rendered Agent2 input.
    """
    context_items: Dict[str, Dict[str, str]] = {}
    pattern = re.compile(r"^- \[([^\]]+)\]\s+(.*?)(?:\s+\(|$)", re.M)
    for match in pattern.finditer(requirement_text):
        item_id = match.group(1).strip()
        text = match.group(2).strip()
        if not item_id:
            continue
        if item_id.startswith("rule_"):
            section = "business_rules"
        elif item_id.startswith("constraint_"):
            section = "constraints"
        elif item_id.startswith("unknown_"):
            section = "unknowns"
        elif item_id.startswith("fact_"):
            section = "confirmed_facts"
        elif item_id.startswith("flow_"):
            section = "process_flows"
        else:
            section = "unknown"
        context_items[item_id] = {
            "id": item_id,
            "text": text,
            "section": section,
        }
    return context_items


def _constraint_texts(context_items: Dict[str, Dict[str, str]]) -> set[str]:
    return {
        _normalize_match_text(item["text"])
        for item in context_items.values()
        if item.get("section") == "constraints"
    }


def _split_known_conditions(
    known_conditions: List[str],
    context_items: Dict[str, Dict[str, str]],
) -> Tuple[List[str], List[str]]:
    constraints: List[str] = []
    rules: List[str] = []
    known_constraint_texts = _constraint_texts(context_items)
    constraint_markers = ["不允许", "不可", "不能", "只读", "禁止"]

    for condition in known_conditions:
        normalized = _normalize_match_text(condition)
        is_constraint = (
            normalized in known_constraint_texts
            or any(marker in condition for marker in constraint_markers)
        )
        if is_constraint:
            constraints.append(condition)
        else:
            rules.append(condition)
    return rules, constraints


def _candidate_by_action(parsing_result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    candidates: Dict[str, Dict[str, Any]] = {}
    for candidate in parsing_result.get("action_gap_candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        action = str(candidate.get("action", "")).strip()
        if action:
            candidates[action] = candidate
    return candidates


def _risk_type_for_question(
    *,
    question: str,
    specific_unknown: str,
    risk_result: Dict[str, Any],
) -> Tuple[str, str]:
    match_targets = [
        _normalize_match_text(specific_unknown),
        _normalize_match_text(question),
    ]

    for field, risk_type in [
        ("edge_case_risks", "edge_case"),
        ("permission_risks", "permission"),
        ("data_risks", "data"),
        ("performance_risks", "performance"),
        ("ambiguity_risks", "ambiguity"),
    ]:
        for risk_text in _normalize_string_list(risk_result.get(field, [])):
            normalized_risk = _normalize_match_text(risk_text)
            if any(
                target
                and (
                    target in normalized_risk
                    or normalized_risk in target
                )
                for target in match_targets
            ):
                return risk_type, risk_text

    return "ambiguity", specific_unknown or question


def _build_risk_id(
    *,
    risk_type: str,
    description: str,
    context_refs: List[str],
) -> str:
    seed = "|".join([risk_type, description, *context_refs])
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"risk_{risk_type}_{digest}"


def _sanitize_context_refs(
    refs: Any,
    context_items: Dict[str, Dict[str, str]],
) -> List[str]:
    valid_ids = set(context_items)
    return [
        ref
        for ref in _normalize_string_list(refs)
        if ref in valid_ids
    ]


def _build_risk_item_from_question_source(
    *,
    question_source: Dict[str, Any],
    parsing_result: Dict[str, Any],
    risk_result: Dict[str, Any],
    context_items: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    question = str(question_source.get("question", "")).strip()
    action = str(question_source.get("action", "")).strip()
    specific_unknown = str(question_source.get("specific_unknown", "")).strip()
    context_refs = _sanitize_context_refs(
        question_source.get("context_refs", []),
        context_items,
    )
    risk_type, description = _risk_type_for_question(
        question=question,
        specific_unknown=specific_unknown,
        risk_result=risk_result,
    )

    action_candidates = _candidate_by_action(parsing_result)
    related_rules: List[str] = []
    related_constraints: List[str] = []
    if action and action in action_candidates:
        related_rules, related_constraints = _split_known_conditions(
            _normalize_string_list(
                action_candidates[action].get("known_conditions", [])
            ),
            context_items,
        )

    return {
        "risk_id": _build_risk_id(
            risk_type=risk_type,
            description=description,
            context_refs=context_refs,
        ),
        "risk_type": risk_type,
        "description": description,
        "related_unknowns": (
            [specific_unknown] if specific_unknown else []
        ),
        "related_rules": related_rules,
        "related_constraints": related_constraints,
        "context_refs": context_refs,
    }


def _build_risk_item_from_legacy_risk(
    *,
    risk_type: str,
    description: str,
) -> Dict[str, Any]:
    return {
        "risk_id": _build_risk_id(
            risk_type=risk_type,
            description=description,
            context_refs=[],
        ),
        "risk_type": risk_type,
        "description": description,
        "related_unknowns": [],
        "related_rules": [],
        "related_constraints": [],
        "context_refs": [],
    }


def build_risk_items(
    *,
    requirement_text: str,
    parsing_result: Dict[str, Any],
    question_result: Dict[str, Any],
    risk_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build a minimal Agent2 -> Agent3 risk artifact from trusted inputs.
    """
    context_items = _extract_context_items_from_rendered_input(requirement_text)
    risk_items: List[Dict[str, Any]] = []
    covered_descriptions = set()

    for question_source in question_result.get("question_sources", []) or []:
        if not isinstance(question_source, dict):
            continue
        risk_item = _build_risk_item_from_question_source(
            question_source=question_source,
            parsing_result=parsing_result,
            risk_result=risk_result,
            context_items=context_items,
        )
        if not risk_item["description"]:
            continue
        risk_items.append(risk_item)
        covered_descriptions.add(_normalize_match_text(risk_item["description"]))

    for field, risk_type in RISK_ARRAY_FIELDS.items():
        for description in _normalize_string_list(risk_result.get(field, [])):
            normalized_description = _normalize_match_text(description)
            if normalized_description in covered_descriptions:
                continue
            risk_items.append(
                _build_risk_item_from_legacy_risk(
                    risk_type=risk_type,
                    description=description,
                )
            )
            covered_descriptions.add(normalized_description)

    return risk_items


def normalize_output(
    *,
    requirement_text: str,
    parsing_result: Dict[str, Any],
    question_result: Dict[str, Any],
    result: Dict[str, Any],
) -> Dict[str, Any]:
    normalized_result = dict(result)
    for field in LEGACY_RISK_FIELDS:
        normalized_result[field] = _normalize_string_list(
            normalized_result.get(field, [])
        )

    normalized_result["risk_items"] = build_risk_items(
        requirement_text=requirement_text,
        parsing_result=parsing_result,
        question_result=question_result,
        risk_result=normalized_result,
    )
    return normalized_result


def run_agent2_risk(requirement_text: str,parsing_result: Dict[str, Any],question_result: Dict[str, Any],) -> Dict[str, Any]:

    """
    执行 Agent2 风险分析。

    输入：
    - requirement_text: 原始需求文本
    - parsing_result: Agent1 解析结果

    输出：
    - Agent2 风险分析结果
    """
    prompt = load_prompt("prompts/agent_2_risk_review.md")
    payload = {
        "requirement_text": requirement_text,
        "agent_1_requirement_parsing": parsing_result,
        "agent_1_questions": question_result,
    }
    raw_result = call_llm(prompt, payload)
    parsed_result = parse_json_result(raw_result)
    return normalize_output(
        requirement_text=requirement_text,
        parsing_result=parsing_result,
        question_result=question_result,
        result=parsed_result,
    )
