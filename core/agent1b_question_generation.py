"""
Agent1B：问题生成。

作用：
- 读取 Agent1B prompt
- 基于 requirement_text、main_flow、action_gap_candidates 调用大模型
- 生成最终 open_questions
- 返回标准化问题结果

主要流程：
1. 读取 prompts/agent1b_question_generation.md
2. 组装输入 payload
3. 调用统一 LLM 封装
4. 解析 JSON
5. 对 open_questions 做最小兜底修正

设计考虑：
- 该模块只负责“问题表达”，不重新判断缺口
- 输入必须依赖 Agent1A 的输出，避免任务重新缠绕
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.llm_client import call_llm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "agent1b_question_generation.md"


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


def build_payload(
    requirement_text: str,
    main_flow: List[str],
    action_gap_candidates: List[Dict[str, Any]],
    unassigned_unknowns: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    构造发送给模型的输入 payload。

    输入：
    - requirement_text: 原始需求文本
    - main_flow: 动作列表
    - action_gap_candidates: 动作缺口候选列表

    输出：
    - payload 字典
    """
    payload = {
        "requirement_text": requirement_text,
        "main_flow": main_flow,
        "action_gap_candidates": action_gap_candidates,
    }
    if unassigned_unknowns:
        payload["unassigned_unknowns"] = unassigned_unknowns
    return payload


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


def normalize_open_questions(open_questions: Any) -> List[str]:
    """
    规范 open_questions 字段，保证类型稳定。

    输入：
    - open_questions: 模型输出的原始问题列表

    输出：
    - 规范化后的问题列表
    """
    if not isinstance(open_questions, list):
        return []

    normalized_questions: List[str] = []
    for item in open_questions:
        if not isinstance(item, str):
            continue

        question = item.strip()
        if not question:
            continue

        normalized_questions.append(question)

    return normalized_questions


def normalize_question_sources(question_sources: Any) -> List[Dict[str, Any]]:
    """
    Normalize question_sources so Trace can show where each question came from.
    """
    if not isinstance(question_sources, list):
        return []

    normalized_sources: List[Dict[str, Any]] = []
    for item in question_sources:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        action = str(item.get("action", "")).strip()
        specific_unknown = str(item.get("specific_unknown", "")).strip()
        unassigned = bool(item.get("unassigned", False))
        raw_context_refs = item.get("context_refs", [])
        if not isinstance(raw_context_refs, list):
            raw_context_refs = []

        context_refs = [
            str(context_ref).strip()
            for context_ref in raw_context_refs
            if str(context_ref).strip()
        ]

        if not question:
            continue

        normalized_sources.append(
            {
                "question": question,
                "action": action,
                "specific_unknown": specific_unknown,
                "context_refs": context_refs,
                "unassigned": unassigned,
            }
        )

    return normalized_sources


def _clean_unknown_topic(specific_unknown: str) -> str:
    topic = specific_unknown.strip().rstrip("。；;，, ")
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
        if topic.startswith(prefix):
            topic = topic[len(prefix):].strip()
            break

    topic = topic.lstrip("：:，, 的")
    for suffix in ["未确定", "未定义", "未明确", "待确认"]:
        if topic.endswith(suffix):
            topic = topic[: -len(suffix)].strip()
            break

    return topic.strip() or specific_unknown.strip().rstrip("。；;，, ")


def _question_from_specific_unknown(
    specific_unknown: str,
    *,
    action: str = "",
) -> str:
    topic = _clean_unknown_topic(specific_unknown)
    action_text = action.strip()

    if "是否" in topic:
        question = f"{topic}？"
    else:
        question = f"{topic}是什么？"

    if action_text:
        return f"在“{action_text}”中，{question}"
    return question


def _build_specific_unknown_question_sources(
    action_gap_candidates: List[Dict[str, Any]],
    unassigned_unknowns: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    question_sources: List[Dict[str, Any]] = []
    seen_questions = set()

    for candidate in action_gap_candidates:
        if not isinstance(candidate, dict) or not candidate.get("has_gap"):
            continue

        action = str(candidate.get("action", "")).strip()
        specific_unknowns = candidate.get("specific_unknowns", [])
        context_refs = candidate.get("context_refs", [])
        if not isinstance(specific_unknowns, list):
            specific_unknowns = []
        if not isinstance(context_refs, list):
            context_refs = []

        for index, raw_unknown in enumerate(specific_unknowns):
            specific_unknown = str(raw_unknown).strip()
            if not specific_unknown:
                continue

            question = _question_from_specific_unknown(
                specific_unknown,
                action=action,
            )
            if question in seen_questions:
                continue
            seen_questions.add(question)

            source_context_refs: List[str] = []
            if index < len(context_refs):
                context_ref = str(context_refs[index]).strip()
                if context_ref:
                    source_context_refs.append(context_ref)

            question_sources.append(
                {
                    "question": question,
                    "action": action,
                    "specific_unknown": specific_unknown,
                    "context_refs": source_context_refs,
                    "unassigned": False,
                }
            )

    for unassigned_unknown in unassigned_unknowns or []:
        specific_unknown = str(
            unassigned_unknown.get("specific_unknown")
            or unassigned_unknown.get("text")
            or ""
        ).strip()
        if not specific_unknown:
            continue

        action = str(unassigned_unknown.get("assigned_action", "")).strip()
        question = _question_from_specific_unknown(
            specific_unknown,
            action=action,
        )
        if question in seen_questions:
            continue
        seen_questions.add(question)

        raw_context_refs = unassigned_unknown.get("context_refs", [])
        if not isinstance(raw_context_refs, list):
            raw_context_refs = []
        context_refs = [
            str(context_ref).strip()
            for context_ref in raw_context_refs
            if str(context_ref).strip()
        ]

        question_sources.append(
            {
                "question": question,
                "action": action,
                "specific_unknown": specific_unknown,
                "context_refs": context_refs,
                "unassigned": True,
            }
        )

    return question_sources


def normalize_output(
    result: Dict[str, Any],
    action_gap_candidates: List[Dict[str, Any]] | None = None,
    unassigned_unknowns: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    对 Agent1B 输出做最小兜底修正。

    输入：
    - result: 模型解析结果

    输出：
    - 规范化后的结果字典
    """
    specific_unknown_sources = _build_specific_unknown_question_sources(
        action_gap_candidates or [],
        unassigned_unknowns=unassigned_unknowns,
    )
    if specific_unknown_sources:
        return {
            "open_questions": [
                source["question"] for source in specific_unknown_sources
            ],
            "question_sources": specific_unknown_sources,
        }

    open_questions = normalize_open_questions(result.get("open_questions", []))
    question_sources = normalize_question_sources(result.get("question_sources", []))
    return {
        "open_questions": open_questions,
        "question_sources": question_sources,
    }


def run_agent1b_question_generation(
    requirement_text: str,
    main_flow: List[str],
    action_gap_candidates: List[Dict[str, Any]],
    unassigned_unknowns: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    执行 Agent1B：问题生成。

    输入：
    - requirement_text: 原始需求文本
    - main_flow: 动作列表
    - action_gap_candidates: Agent1A 输出的动作缺口候选

    输出：
    - Agent1B 的 open_questions 结果
    """
    # 读取 prompt 并构造输入
    prompt = load_prompt(PROMPT_PATH)
    payload = build_payload(
        requirement_text=requirement_text,
        main_flow=main_flow,
        action_gap_candidates=action_gap_candidates,
        unassigned_unknowns=unassigned_unknowns,
    )

    # 调用模型并解析输出
    raw_response = call_llm(prompt=prompt, payload=payload)
    parsed_result = parse_json_response(raw_response)

    # 规范化 open_questions
    return normalize_output(
        parsed_result,
        action_gap_candidates=action_gap_candidates,
        unassigned_unknowns=unassigned_unknowns,
    )
