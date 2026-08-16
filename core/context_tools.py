"""
Minimal context provider utilities.

This module returns context packages for Workflow State and does not call
Agents, route the pipeline, or decide whether the Workflow should continue
after a context failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.repository_context_skill_adapter import (
    PROVIDER_ID as REPOSITORY_CONTEXT_PROVIDER_ID,
    SKILL_ID as REPOSITORY_CONTEXT_SKILL_ID,
    build_repository_context_package,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MARKDOWN_PROVIDER_ID = "local_markdown_context_provider"
LOCAL_MARKDOWN_TOOL_ID = "local_markdown_context_reader"
LOCAL_STRUCTURED_CONTEXT_PROVIDER_ID = "local_structured_context_provider"
LOCAL_STRUCTURED_CONTEXT_TOOL_ID = "local_structured_context_reader"

CONTEXT_PACKAGE_V2_REQUIRED_SECTIONS = [
    "confirmed_facts",
    "business_rules",
    "constraints",
    "process_flows",
    "unknowns",
    "source_refs",
]

AGENT_CONTEXT_SECTIONS = {
    "agent1a": [
        "confirmed_facts",
        "business_rules",
        "constraints",
        "process_flows",
        "unknowns",
    ],
    # Agent1B should express clarification questions from Agent1A Stage
    # Artifact instead of re-reading the full Context View.
    "agent1b": [],
    "agent2": [
        "confirmed_facts",
        "business_rules",
        "constraints",
        "process_flows",
        "unknowns",
        "quality_flags",
    ],
    "agent3": [
        "confirmed_facts",
        "business_rules",
        "constraints",
        "process_flows",
        "unknowns",
    ],
    "agent4": [
        "confirmed_facts",
        "business_rules",
        "constraints",
        "process_flows",
        "unknowns",
        "source_refs",
        "quality_flags",
    ],
}

SECTION_LABELS = {
    "confirmed_facts": "已确认事实",
    "business_rules": "业务规则",
    "constraints": "限制条件",
    "process_flows": "流程信息",
    "unknowns": "已知未知项",
    "source_refs": "来源信息",
    "quality_flags": "质量标记",
}

AGENT_CONTEXT_NOTES = {
    "agent1a": (
        "unknowns 只能用于识别具体缺口，不能作为已确认事实；"
        "不要把 confirmed_facts、business_rules、constraints 中已有的信息再次识别为宽泛缺口。"
    ),
    "agent1b": (
        "澄清问题应优先来自 unknowns；不要重复询问 confirmed_facts、business_rules、constraints 中已经回答的问题。"
    ),
    "agent2": (
        "风险分析应引用已知规则和限制；unknowns 只能作为信息缺失风险来源，不能自行补全。"
    ),
    "agent3": (
        "测试草案可以覆盖已知规则和限制；unknowns 只能作为待确认或信息不足项，不能生成确定性断言。"
    ),
    "agent4": (
        "汇总应区分已确认信息和待确认信息，并保留来源边界；不要新增上游没有提供的事实。"
    ),
}


def _resolve_source_path(path_value: str) -> Path:
    source_path = Path(path_value)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path
    return source_path


def _get_source_id(source: Dict[str, Any]) -> str:
    return source.get("source_id") or source.get("id") or "markdown_context"


def _is_required_source(source: Dict[str, Any]) -> bool:
    return bool(source.get("required", False))


def _build_context_error(
    *,
    source_id: str,
    error: Exception,
) -> Dict[str, str]:
    return {
        "stage_id": f"context:{source_id}",
        "error_type": type(error).__name__,
        "message": str(error),
    }


def _build_failed_context_package(
    *,
    source: Dict[str, Any],
    error: Exception,
    provider_id: str | None = None,
    capability_id: str | None = None,
    capability_type: str | None = None,
) -> Dict[str, Any]:
    source_id = _get_source_id(source)
    resolved_capability_type = capability_type or _capability_type_for_source(source)
    resolved_capability_id = capability_id or _capability_id_for_source(source)
    return {
        "context_id": source_id,
        "provider_id": provider_id or _provider_id_for_source(source),
        "tool_id": (
            resolved_capability_id
            if resolved_capability_type == "tool"
            else None
        ),
        "skill_id": (
            resolved_capability_id
            if resolved_capability_type == "skill"
            else None
        ),
        "capability_type": resolved_capability_type,
        "source": source,
        "required": _is_required_source(source),
        "content_type": source.get("type"),
        "content": None,
        "status": "failed",
        "error": _build_context_error(source_id=source_id, error=error),
    }


def _provider_id_for_source(source: Dict[str, Any]) -> str:
    if source.get("type") == "local_repository":
        return REPOSITORY_CONTEXT_PROVIDER_ID
    if source.get("type") == "local_structured_context":
        return LOCAL_STRUCTURED_CONTEXT_PROVIDER_ID
    return LOCAL_MARKDOWN_PROVIDER_ID


def _capability_id_for_source(source: Dict[str, Any]) -> str:
    if source.get("type") == "local_repository":
        return REPOSITORY_CONTEXT_SKILL_ID
    if source.get("type") == "local_structured_context":
        return LOCAL_STRUCTURED_CONTEXT_TOOL_ID
    return LOCAL_MARKDOWN_TOOL_ID


def _capability_type_for_source(source: Dict[str, Any]) -> str:
    if source.get("type") == "local_repository":
        return "skill"
    return "tool"


def _validate_structured_context_v2(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Structured context must be a JSON object")

    version = data.get("context_package_version")
    if version != "v2":
        raise ValueError("Structured context requires context_package_version='v2'")

    structured_content = data.get("structured_content")
    if not isinstance(structured_content, dict):
        raise ValueError("Structured context requires structured_content object")

    for section in CONTEXT_PACKAGE_V2_REQUIRED_SECTIONS:
        if section not in structured_content:
            raise ValueError(f"Structured context missing section: {section}")
        if not isinstance(structured_content[section], list):
            raise ValueError(f"Structured context section must be a list: {section}")

    for section, items in structured_content.items():
        if not isinstance(items, list):
            raise ValueError(f"Structured context section must be a list: {section}")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Structured context item must be an object: {section}[{index}]"
                )
            if not item.get("id"):
                raise ValueError(
                    f"Structured context item missing id: {section}[{index}]"
                )
            if not item.get("text"):
                raise ValueError(
                    f"Structured context item missing text: {section}[{index}]"
                )


def _structured_item_ref(
    *,
    agent_id: str,
    section: str,
    item_id: str,
) -> str:
    return f"agent_context_view.{agent_id}.{section}.{item_id}"


def _normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    normalized_items = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized_items.append(text)
    return normalized_items


def _normalize_match_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    for char in [" ", "\t", "\n", "\r", "。", "，", "、", "：", ":", "；", ";"]:
        text = text.replace(char, "")
    for word in ["自己的", "自己"]:
        text = text.replace(word, "")
    return text


def _find_action_by_applies_to(
    *,
    applies_to: List[str],
    actions: List[str],
) -> Tuple[str | None, str]:
    if not applies_to or not actions:
        return None, "unassigned"

    normalized_actions = [
        (action, _normalize_match_text(action))
        for action in actions
        if str(action).strip()
    ]

    for applies_to_item in applies_to:
        normalized_applies_to = _normalize_match_text(applies_to_item)
        exact_matches = [
            action
            for action, normalized_action in normalized_actions
            if normalized_action == normalized_applies_to
        ]
        if len(exact_matches) == 1:
            return exact_matches[0], "applies_to_exact"

    for applies_to_item in applies_to:
        normalized_applies_to = _normalize_match_text(applies_to_item)
        if not normalized_applies_to:
            continue

        contains_matches = [
            action
            for action, normalized_action in normalized_actions
            if (
                normalized_applies_to in normalized_action
                or normalized_action in normalized_applies_to
            )
        ]
        unique_matches = list(dict.fromkeys(contains_matches))
        if len(unique_matches) == 1:
            return unique_matches[0], "applies_to_contains"
        if len(unique_matches) > 1:
            return None, "ambiguous_applies_to"

    return None, "unassigned"


def read_local_markdown_context(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read a local Markdown context source and return one context package.
    """
    source_id = _get_source_id(source)
    path_value = source.get("path", "")
    source_path = _resolve_source_path(path_value)

    if source.get("type") != "local_markdown":
        raise ValueError(f"Unsupported context source type: {source.get('type')}")

    if source_path.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError(f"Context source is not a Markdown file: {source_path}")

    content = source_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Context source is empty: {source_path}")

    return {
        "context_id": source_id,
        "provider_id": LOCAL_MARKDOWN_PROVIDER_ID,
        "tool_id": LOCAL_MARKDOWN_TOOL_ID,
        "skill_id": None,
        "capability_type": "tool",
        "source": {
            "type": "local_markdown",
            "path": str(source_path),
        },
        "required": _is_required_source(source),
        "content_type": "markdown",
        "content": content,
        "status": "success",
        "error": None,
    }


def read_local_structured_context(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read a local structured Context Package V2 source.
    """
    path_value = source.get("path", "")
    source_path = _resolve_source_path(path_value)

    if source.get("type") != "local_structured_context":
        raise ValueError(f"Unsupported context source type: {source.get('type')}")

    if source_path.suffix.lower() != ".json":
        raise ValueError(
            f"Structured context source is not a JSON file: {source_path}"
        )

    with source_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    _validate_structured_context_v2(data)

    source_id = str(data.get("context_id") or source_path.stem).strip()
    structured_content = data["structured_content"]
    return {
        "context_id": source_id,
        "provider_id": LOCAL_STRUCTURED_CONTEXT_PROVIDER_ID,
        "tool_id": LOCAL_STRUCTURED_CONTEXT_TOOL_ID,
        "skill_id": None,
        "capability_type": "tool",
        "source": {
            "type": "local_structured_context",
            "path": str(source_path),
        },
        "required": _is_required_source(source),
        "context_origin": data.get("context_origin"),
        "context_package_version": "v2",
        "content_type": "structured_context_v2",
        "content": data.get("summary", ""),
        "structured_content": structured_content,
        "status": "success",
        "error": None,
    }


def _resolve_repository_root(path_value: str) -> Path:
    if not path_value:
        raise ValueError("Repository context source requires a path")

    source_path = _resolve_source_path(path_value).resolve()
    project_root = PROJECT_ROOT.resolve()

    if not source_path.is_dir():
        raise ValueError(f"Repository context source is not a directory: {source_path}")

    if source_path != project_root and project_root not in source_path.parents:
        raise ValueError(
            f"Repository context source must stay inside project root: {source_path}"
        )

    return source_path


def read_repository_context_skill(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load repository context through the repository Skill adapter boundary.
    """
    source_id = _get_source_id(source)
    repository_root = _resolve_repository_root(source.get("path", ""))
    return build_repository_context_package(
        source_id=source_id,
        source=source,
        repository_root=repository_root,
        required=_is_required_source(source),
    )


def load_context_source(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load one context source through the standard Context Provider entry point.

    The provider returns a success or failed Context Package. It deliberately
    does not decide whether the Workflow should stop or continue.
    """
    try:
        if source.get("type") == "local_markdown":
            return read_local_markdown_context(source)
        if source.get("type") == "local_structured_context":
            return read_local_structured_context(source)
        if source.get("type") == "local_repository":
            return read_repository_context_skill(source)
        else:
            raise ValueError(
                f"Unsupported context source type: {source.get('type')}"
            )
    except Exception as error:
        return _build_failed_context_package(source=source, error=error)


def build_context_augmented_requirement(
    *,
    requirement_text: str,
    context_items: list[Dict[str, Any]],
) -> str:
    """
    Append successful context items to the requirement text for Agent1A.
    """
    successful_items = [
        item for item in context_items
        if item.get("status") == "success" and item.get("content")
    ]
    if not successful_items:
        return requirement_text

    context_blocks = []
    for item in successful_items:
        context_blocks.append(
            "\n".join(
                [
                    f"[context_id: {item.get('context_id')}]",
                    f"[source_type: {item.get('source', {}).get('type')}]",
                    str(item.get("content", "")),
                ]
            )
        )

    return (
        f"{requirement_text}\n\n"
        "【补充上下文材料】\n"
        + "\n\n".join(context_blocks)
    )


def build_legacy_context_fidelity_audit(
    *,
    context_items: List[Dict[str, Any]],
    agent1_result: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Summarize how raw non-V2 context was consumed by Agent1A.

    Markdown context has no item-level structure, so this audit shows which
    raw sources entered Agent1A and which action-level facts/unknowns Agent1A
    preserved for downstream stages. It does not assert semantic coverage.
    """
    raw_context_sources = []
    for item in context_items:
        if item.get("context_package_version") == "v2":
            continue
        if item.get("status") != "success":
            continue
        content = str(item.get("content") or "")
        raw_context_sources.append(
            {
                "context_id": item.get("context_id"),
                "content_type": item.get("content_type"),
                "source": item.get("source"),
                "content_length": len(content),
                "content_preview": " ".join(content.split())[:500],
            }
        )

    action_gap_candidates = []
    for candidate in (agent1_result or {}).get("action_gap_candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        action_gap_candidates.append(
            {
                "action": candidate.get("action"),
                "known_conditions": candidate.get("known_conditions", []),
                "specific_unknowns": candidate.get("specific_unknowns", []),
                "context_refs": candidate.get("context_refs", []),
            }
        )

    return {
        "mode": "legacy_raw_context",
        "raw_context_sources": raw_context_sources,
        "agent1a_extracted_action_gap_candidates": action_gap_candidates,
        "loss_check_note": (
            "Raw Markdown context is not itemized. Downstream stages only receive "
            "what Agent1A preserved in its stage artifact."
        ),
    }


def _successful_v2_context_items(
    context_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return [
        item
        for item in context_items
        if (
            item.get("status") == "success"
            and item.get("context_package_version") == "v2"
            and isinstance(item.get("structured_content"), dict)
        )
    ]


def _is_consumable_context_item(
    *,
    context_package: Dict[str, Any],
    item: Dict[str, Any],
) -> bool:
    """
    Keep auto-prepared candidates out of Agent Context Views until reviewed.

    Manually prepared V2 packages stay compatible. The strict gate only applies
    to packages explicitly marked with context_origin="auto_prepared".
    """
    if context_package.get("context_origin") != "auto_prepared":
        return True

    return (
        item.get("source_verified") is True
        and item.get("human_confirmed") is True
        and item.get("review_status") == "approved"
        and item.get("version_status") == "active"
        and item.get("conflict_status") == "none"
        and item.get("scope_status") == "matched"
    )


def build_agent_context_view(
    *,
    agent_id: str,
    context_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build an Agent-specific Context View without mutating Workflow State.
    """
    sections = AGENT_CONTEXT_SECTIONS.get(agent_id, [])
    v2_items = _successful_v2_context_items(context_items)
    if not sections or not v2_items:
        return {
            "agent_id": agent_id,
            "context_package_version": None,
            "sections": {},
            "guidance": None,
        }

    view_sections: Dict[str, Any] = {}
    for section in sections:
        section_entries = []
        for context_item in v2_items:
            context_id = context_item.get("context_id")
            structured_content = context_item.get("structured_content", {})
            for item in structured_content.get(section, []):
                if not _is_consumable_context_item(
                    context_package=context_item,
                    item=item,
                ):
                    continue
                item_id = item.get("id")
                section_entries.append(
                    {
                        "context_id": context_id,
                        "id": item_id,
                        "text": item.get("text"),
                        "applies_to": _normalize_string_list(
                            item.get("applies_to", [])
                        ),
                        "applies_to_candidates": _normalize_string_list(
                            item.get("applies_to_candidates", [])
                        ),
                        "source_ref": item.get("source_ref"),
                        "confidence": item.get("confidence"),
                        "input_ref": _structured_item_ref(
                            agent_id=agent_id,
                            section=section,
                            item_id=item_id,
                        ),
                    }
                )
        if section_entries:
            view_sections[section] = section_entries

    if not view_sections:
        return {
            "agent_id": agent_id,
            "context_package_version": None,
            "sections": {},
            "guidance": None,
        }

    return {
        "agent_id": agent_id,
        "context_package_version": "v2",
        "sections": view_sections,
        "guidance": AGENT_CONTEXT_NOTES.get(agent_id),
    }


def build_context_consumption(
    context_view: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Summarize concrete Context item IDs consumed by one Agent view.
    """
    consumption: Dict[Tuple[str, str], List[str]] = {}
    for section, entries in context_view.get("sections", {}).items():
        for entry in entries:
            key = (entry.get("context_id"), section)
            consumption.setdefault(key, []).append(entry.get("id"))

    return [
        {
            "context_id": context_id,
            "section": section,
            "item_ids": item_ids,
        }
        for (context_id, section), item_ids in consumption.items()
    ]


def build_final_input_sources(
    *,
    context_view: Dict[str, Any],
) -> List[str]:
    sources = ["workflow_state.input.requirement_text"]
    for entries in context_view.get("sections", {}).values():
        for entry in entries:
            if entry.get("input_ref"):
                sources.append(entry["input_ref"])
    return sources


def build_context_source_summary(
    context_view: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build a compact source summary from one Agent Context View.
    """
    summary: List[Dict[str, Any]] = []
    for section, entries in context_view.get("sections", {}).items():
        for entry in entries:
            summary.append(
                {
                    "section": section,
                    "context_id": entry.get("context_id"),
                    "item_id": entry.get("id"),
                    "text": entry.get("text"),
                    "source_ref": entry.get("source_ref"),
                    "input_ref": entry.get("input_ref"),
                }
            )
    return summary


def build_rendered_agent_input(
    *,
    requirement_text: str,
    context_view: Dict[str, Any],
) -> str:
    """
    Render the original requirement plus one Agent-specific Context View.

    The original requirement stored in Workflow State is not modified.
    """
    sections = context_view.get("sections", {})
    if not sections:
        return requirement_text

    lines = [
        requirement_text,
        "",
        "【Agent 专属 Context View】",
        f"agent_id: {context_view.get('agent_id')}",
    ]
    if context_view.get("guidance"):
        lines.extend(["", "使用边界:", f"- {context_view['guidance']}"])

    for section, entries in sections.items():
        lines.extend(["", f"{SECTION_LABELS.get(section, section)}:"])
        for entry in entries:
            source_ref = entry.get("source_ref") or "unknown_source"
            confidence = entry.get("confidence") or "unknown"
            applies_to = entry.get("applies_to") or []
            applies_to_candidates = entry.get("applies_to_candidates") or []
            applies_to_text = ""
            if applies_to:
                applies_to_text = f", applies_to={';'.join(applies_to)}"
            elif applies_to_candidates:
                applies_to_text = (
                    f", applies_to_candidates={';'.join(applies_to_candidates)}"
                )
            lines.append(
                f"- [{entry.get('id')}] {entry.get('text')} "
                f"(source_ref={source_ref}, confidence={confidence}{applies_to_text})"
            )

    return "\n".join(lines)


def _v2_unknown_items(context_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unknown_items: List[Dict[str, Any]] = []
    for context_item in _successful_v2_context_items(context_items):
        context_id = context_item.get("context_id")
        structured_content = context_item.get("structured_content", {})
        for item in structured_content.get("unknowns", []):
            if not _is_consumable_context_item(
                context_package=context_item,
                item=item,
            ):
                continue
            unknown_items.append(
                {
                    "context_id": context_id,
                    "id": item.get("id"),
                    "text": item.get("text"),
                    "applies_to": _normalize_string_list(item.get("applies_to", [])),
                    "applies_to_candidates": _normalize_string_list(
                        item.get("applies_to_candidates", [])
                    ),
                }
            )
    return unknown_items


def _normalize_candidate_string_list(value: Any) -> List[str]:
    return _normalize_string_list(value)


def _clean_unknown_for_downstream(value: Any) -> str:
    text = str(value or "").strip().rstrip("。；;，, ")
    for prefix in [
        "当前没有定义",
        "当前未定义",
        "当前未明确",
        "没有定义",
        "未定义",
        "未明确",
        "未确定",
        "待确认",
    ]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    text = text.lstrip("：:，, 的")
    if not text:
        return ""
    if text.endswith(("未明确", "未定义", "未确定", "待确认")):
        return text
    return f"{text}未明确"


def _clean_unknowns_for_downstream(values: List[str]) -> List[str]:
    cleaned_values: List[str] = []
    for value in values:
        cleaned = _clean_unknown_for_downstream(value)
        if cleaned and cleaned not in cleaned_values:
            cleaned_values.append(cleaned)
    return cleaned_values


def _remove_v2_unknowns_from_candidate(
    *,
    candidate: Dict[str, Any],
    unknown_by_id: Dict[str, Dict[str, Any]],
    unknown_texts: set[str],
) -> None:
    specific_unknowns = _normalize_candidate_string_list(
        candidate.get("specific_unknowns", [])
    )
    context_refs = _normalize_candidate_string_list(candidate.get("context_refs", []))

    kept_unknowns: List[str] = []
    kept_refs: List[str] = []
    for index, unknown_text in enumerate(specific_unknowns):
        context_ref = context_refs[index] if index < len(context_refs) else ""
        if context_ref in unknown_by_id:
            continue
        if _normalize_match_text(unknown_text) in unknown_texts:
            continue
        kept_unknowns.append(unknown_text)
        if context_ref:
            kept_refs.append(context_ref)

    candidate["specific_unknowns"] = kept_unknowns
    candidate["context_refs"] = kept_refs


def _append_unknown_to_candidate(
    *,
    candidate: Dict[str, Any],
    unknown_item: Dict[str, Any],
    remaining_unknowns: List[str] | None = None,
) -> None:
    candidate.setdefault("specific_unknowns", [])
    candidate.setdefault("context_refs", [])

    unknown_texts = remaining_unknowns or [unknown_item["text"]]
    for unknown_text in unknown_texts:
        if unknown_text not in candidate["specific_unknowns"]:
            candidate["specific_unknowns"].append(unknown_text)
            candidate["context_refs"].append(unknown_item["id"])

    candidate["has_gap"] = True
    if not candidate.get("gap_type"):
        candidate["gap_type"] = "rule"


def _context_unknown_assessment_by_ref(
    agent1_result: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    assessments: Dict[str, Dict[str, Any]] = {}
    for item in agent1_result.get("context_unknown_assessments", []) or []:
        if not isinstance(item, dict):
            continue
        context_ref = str(item.get("context_ref", "")).strip()
        if context_ref:
            assessments[context_ref] = item
    return assessments


def align_action_gap_candidates_with_context(
    *,
    agent1_result: Dict[str, Any],
    context_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Reassign Context V2 unknowns to actions using explicit applies_to first.

    This is a deterministic Stage Contract post-process. It does not call an
    Agent and does not infer missing business rules.
    """
    unknown_items = _v2_unknown_items(context_items)
    action_gap_candidates = agent1_result.get("action_gap_candidates", [])
    if not unknown_items or not isinstance(action_gap_candidates, list):
        return agent1_result

    action_names = [
        str(candidate.get("action", "")).strip()
        for candidate in action_gap_candidates
        if isinstance(candidate, dict) and str(candidate.get("action", "")).strip()
    ]
    for action in agent1_result.get("main_flow", []):
        action_text = str(action).strip()
        if action_text and action_text not in action_names:
            action_names.append(action_text)

    candidate_by_action = {
        str(candidate.get("action", "")).strip(): candidate
        for candidate in action_gap_candidates
        if isinstance(candidate, dict)
        and str(candidate.get("action", "")).strip()
    }

    unknown_by_id = {
        str(item.get("id")): item
        for item in unknown_items
        if item.get("id") and item.get("text")
    }
    unknown_texts = {
        _normalize_match_text(item["text"])
        for item in unknown_by_id.values()
    }

    for candidate in candidate_by_action.values():
        _remove_v2_unknowns_from_candidate(
            candidate=candidate,
            unknown_by_id=unknown_by_id,
            unknown_texts=unknown_texts,
        )

    alignment_records: List[Dict[str, Any]] = []
    unassigned_unknowns: List[Dict[str, Any]] = []
    assessment_by_ref = _context_unknown_assessment_by_ref(agent1_result)

    for unknown_item in unknown_by_id.values():
        assessment = assessment_by_ref.get(unknown_item["id"], {})
        resolution_status = str(
            assessment.get("resolution_status") or "unresolved"
        ).strip()
        remaining_unknowns = _normalize_string_list(
            assessment.get("remaining_unknowns", [])
        )
        if resolution_status == "fully_resolved":
            alignment_records.append(
                {
                    "context_ref": unknown_item["id"],
                    "unknown": unknown_item["text"],
                    "assigned_action": "",
                    "status": "resolved_by_requirement",
                    "alignment_method": "context_unknown_assessment",
                    "remaining_unknowns": [],
                }
            )
            continue

        applies_to = unknown_item.get("applies_to", [])
        applies_to_candidates = unknown_item.get("applies_to_candidates", [])
        applies_to_values = applies_to or applies_to_candidates
        assigned_action, method = _find_action_by_applies_to(
            applies_to=applies_to_values,
            actions=action_names,
        )
        if applies_to_candidates and not applies_to:
            method = (
                "applies_to_candidates_" + method
                if method != "unassigned"
                else method
            )

        unresolved_texts = _clean_unknowns_for_downstream(
            remaining_unknowns or [unknown_item["text"]]
        )
        if not unresolved_texts:
            unresolved_texts = [unknown_item["text"]]

        if assigned_action and assigned_action in candidate_by_action:
            _append_unknown_to_candidate(
                candidate=candidate_by_action[assigned_action],
                unknown_item=unknown_item,
                remaining_unknowns=unresolved_texts,
            )
            alignment_records.append(
                {
                    "context_ref": unknown_item["id"],
                    "unknown": unknown_item["text"],
                    "assigned_action": assigned_action,
                    "status": "assigned",
                    "alignment_method": method,
                    "resolution_status": resolution_status,
                    "remaining_unknowns": unresolved_texts,
                }
            )
        else:
            unassigned_unknown = {
                "specific_unknown": unresolved_texts[0],
                "context_refs": [unknown_item["id"]],
                "applies_to": applies_to_values,
                "alignment_status": "unassigned",
                "alignment_method": method,
                "resolution_status": resolution_status,
            }
            if len(unresolved_texts) > 1:
                unassigned_unknown["remaining_unknowns"] = unresolved_texts
            unassigned_unknowns.append(unassigned_unknown)
            alignment_records.append(
                {
                    "context_ref": unknown_item["id"],
                    "unknown": unknown_item["text"],
                    "assigned_action": "",
                    "status": "unassigned",
                    "alignment_method": method,
                    "resolution_status": resolution_status,
                    "remaining_unknowns": unresolved_texts,
                }
            )

    for candidate in candidate_by_action.values():
        if candidate.get("specific_unknowns"):
            candidate["has_gap"] = True
        elif candidate.get("has_gap") and not candidate.get("context_refs"):
            agent1_result.setdefault("contract_warnings", []).append(
                {
                    "warning_type": "invalid_empty_gap_after_alignment",
                    "action": candidate.get("action", ""),
                    "original_gap_type": candidate.get("gap_type", ""),
                    "message": (
                        "Context alignment removed or failed to assign the "
                        "supporting unknown; normalized empty gap to no gap."
                    ),
                }
            )
            candidate["has_gap"] = False
            candidate["gap_type"] = ""

    agent1_result["action_context_alignment"] = alignment_records
    agent1_result["unassigned_unknowns"] = unassigned_unknowns
    return agent1_result
