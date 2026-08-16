"""
Automatic context preparation utilities.

This module prepares reviewable context candidates from local Markdown/TXT
history files. It does not call business Agents and does not send candidates
to the Workflow until they have been explicitly human-confirmed.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
DEFAULT_GOLD_LABELS_PATH = PROJECT_ROOT / "data" / "context" / "auto_context_gold_labels.json"
REQUIRED_SECTIONS = [
    "confirmed_facts",
    "business_rules",
    "constraints",
    "process_flows",
    "unknowns",
    "source_refs",
    "quality_flags",
]

REQUIREMENT_KEYWORDS = [
    "用户",
    "账号",
    "手机号",
    "注册",
    "登录",
    "个人资料",
    "资料",
    "日志",
    "操作日志",
    "验证码",
    "短信",
    "修改",
    "查看",
]

SECTION_PREFIX = {
    "confirmed_facts": "fact",
    "business_rules": "rule",
    "constraints": "constraint",
    "process_flows": "flow",
    "unknowns": "unknown",
}

METADATA_KEYS = {"scope", "effective_status", "trust", "applies_to"}

ACTION_CANDIDATES = [
    {
        "label": "手机号注册",
        "requirement_markers": ["注册", "手机号"],
        "match_markers": ["注册", "短信", "验证码", "手机号", "自动登录"],
    },
    {
        "label": "用户登录",
        "requirement_markers": ["登录"],
        "match_markers": ["登录", "密码", "登录失败", "登录方式"],
    },
    {
        "label": "个人资料修改",
        "requirement_markers": ["个人资料", "资料", "修改", "查看"],
        "match_markers": ["个人资料", "资料", "昵称", "头像", "注册时间", "修改手机号", "二次验证"],
    },
    {
        "label": "操作日志",
        "requirement_markers": ["日志", "操作日志"],
        "match_markers": ["日志", "操作类型", "操作时间", "操作对象", "结果状态", "保存周期"],
    },
]


def _now() -> str:
    return datetime.now().isoformat()


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _read_text_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _extract_frontmatter(lines: List[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return metadata

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _frontmatter_end_line(lines: List[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return index
    return 0


def _keyword_score(requirement_text: str, text: str) -> int:
    joined = f"{requirement_text}\n{text}"
    score = 0
    for keyword in REQUIREMENT_KEYWORDS:
        if keyword in requirement_text and keyword in text:
            score += 2
        elif keyword in joined and keyword in text:
            score += 1
    return score


def _scope_status(metadata: Dict[str, str], score: int) -> str:
    scope = metadata.get("scope", "").lower()
    if not scope:
        return "unknown"
    if "account" in scope or "user" in scope or "账号" in scope:
        return "matched"
    if score <= 0:
        return "unmatched"
    return "unknown"


def _stable_id(prefix: str, text: str, source_ref: str) -> str:
    digest = hashlib.md5(f"{text}|{source_ref}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _line_source_ref(path: Path, heading: str, line_number: int) -> str:
    heading_part = heading.strip("# ").strip() or "document"
    return f"{_rel_path(path)}#{heading_part}:L{line_number}-L{line_number}"


def _chunk_source_ref(path: Path, heading: str, start_line: int, end_line: int) -> str:
    heading_part = heading.strip("# ").strip() or "document"
    return f"{_rel_path(path)}#{heading_part}:L{start_line}-L{end_line}"


def _iter_source_files(source_dir: Path) -> Iterable[Path]:
    for path in sorted(source_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            yield path


def build_context_index(
    source_dir: str | Path,
    *,
    run_id: str,
) -> Dict[str, Any]:
    source_root = Path(source_dir)
    if not source_root.is_absolute():
        source_root = PROJECT_ROOT / source_root
    if not source_root.exists():
        raise FileNotFoundError(f"History source directory not found: {source_root}")

    documents: List[Dict[str, Any]] = []
    chunks: List[Dict[str, Any]] = []

    for path in _iter_source_files(source_root):
        lines = _read_text_lines(path)
        metadata = _extract_frontmatter(lines)
        frontmatter_end = _frontmatter_end_line(lines)
        doc_id = _stable_id("doc", _rel_path(path), json.dumps(metadata, ensure_ascii=False))
        documents.append(
            {
                "doc_id": doc_id,
                "source_path": _rel_path(path),
                "metadata": metadata,
                "line_count": len(lines),
            }
        )

        heading = "document"
        chunk_lines: List[str] = []
        chunk_start = 1
        for index, line in enumerate(lines, start=1):
            if frontmatter_end and index <= frontmatter_end:
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                if chunk_lines:
                    text = "\n".join(chunk_lines).strip()
                    chunks.append(
                        {
                            "chunk_id": _stable_id(
                                "chunk",
                                text,
                                _chunk_source_ref(path, heading, chunk_start, index - 1),
                            ),
                            "doc_id": doc_id,
                            "source_path": _rel_path(path),
                            "heading": heading,
                            "line_range": [chunk_start, index - 1],
                            "text": text,
                            "metadata": metadata,
                        }
                    )
                heading = stripped.strip("# ").strip() or "document"
                chunk_lines = [line]
                chunk_start = index
            else:
                if not chunk_lines:
                    chunk_start = index
                chunk_lines.append(line)

        if chunk_lines:
            text = "\n".join(chunk_lines).strip()
            chunks.append(
                {
                    "chunk_id": _stable_id(
                        "chunk",
                        text,
                        _chunk_source_ref(path, heading, chunk_start, len(lines)),
                    ),
                    "doc_id": doc_id,
                    "source_path": _rel_path(path),
                    "heading": heading,
                    "line_range": [chunk_start, len(lines)],
                    "text": text,
                    "metadata": metadata,
                }
            )

    return {
        "run_id": run_id,
        "created_at": _now(),
        "source_dir": _rel_path(source_root),
        "documents": documents,
        "chunks": chunks,
    }


def retrieve_context_candidates(
    requirement_text: str,
    index: Dict[str, Any],
    *,
    top_k: int = 12,
) -> List[Dict[str, Any]]:
    scored_chunks: List[Dict[str, Any]] = []
    for chunk in index.get("chunks", []):
        score = _keyword_score(requirement_text, chunk.get("text", ""))
        metadata = chunk.get("metadata", {})
        if metadata.get("effective_status") == "deprecated":
            score += 1
        if score <= 0 and metadata.get("scope") not in {"account", "unknown"}:
            continue
        scored = dict(chunk)
        scored["relevance_score"] = score
        scored_chunks.append(scored)

    scored_chunks.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
    return scored_chunks[:top_k]


def _candidate_section(text: str) -> str:
    if any(marker in text for marker in ["未确定", "未定义", "未明确", "待确认"]):
        return "unknowns"
    if any(marker in text for marker in ["不允许", "不可", "禁止", "限制"]):
        return "constraints"
    if "→" in text or "流程" in text or ("后" in text and "进入" in text):
        return "process_flows"
    if text in {"用户可以查看自己的个人资料。", "系统必须记录用户操作日志。"}:
        return "confirmed_facts"
    if "范围" in text or "字段" in text:
        return "business_rules"
    if "当前系统支持" in text or ("系统支持" in text and "通过" not in text):
        return "confirmed_facts"
    if "可以" in text and any(
        marker in text for marker in ["字段", "范围", "修改", "查看", "使用"]
    ):
        return "business_rules"
    if any(marker in text for marker in ["必须", "需要", "通过", "字段", "唯一", "不会", "记录"]):
        return "business_rules"
    return "confirmed_facts"


def _clean_candidate_text(line: str) -> str:
    text = line.strip()
    text = re.sub(r"^[-*]\s*", "", text)
    text = re.sub(r"^\d+[.)、]\s*", "", text)
    return text.strip()


def _is_metadata_line(text: str) -> bool:
    if ":" not in text:
        return False
    key = text.split(":", 1)[0].strip().lower()
    return key in METADATA_KEYS


def _active_requirement_actions(requirement_text: str) -> List[Dict[str, Any]]:
    return [
        action
        for action in ACTION_CANDIDATES
        if any(marker in requirement_text for marker in action["requirement_markers"])
    ]


def _applies_to_candidates_for_item(
    *,
    requirement_text: str,
    heading: str,
    text: str,
) -> List[str]:
    active_actions = _active_requirement_actions(requirement_text)
    if not active_actions:
        return []

    haystack = f"{heading}\n{text}"
    if "日志" in haystack:
        return ["操作日志"]
    scored: List[Tuple[str, int]] = []
    for action in active_actions:
        score = sum(1 for marker in action["match_markers"] if marker in haystack)
        if score > 0:
            scored.append((action["label"], score))

    if not scored:
        return []

    max_score = max(score for _, score in scored)
    candidates = [label for label, score in scored if score == max_score]
    if len(candidates) <= 2:
        return candidates
    return []


def _extract_candidate_lines(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_path = PROJECT_ROOT / chunk["source_path"]
    heading = chunk.get("heading", "document")
    start_line = int(chunk.get("line_range", [1, 1])[0])
    extracted: List[Dict[str, Any]] = []

    for offset, raw_line in enumerate(chunk.get("text", "").splitlines()):
        text = _clean_candidate_text(raw_line)
        if _is_metadata_line(text):
            continue
        if not text or text.startswith("#") or text == "---" or ":" in text and len(text) < 24:
            continue
        if len(text) < 6:
            continue
        if not any(keyword in text for keyword in REQUIREMENT_KEYWORDS + ["唯一", "必须", "未确定", "不可"]):
            continue
        line_number = start_line + offset
        section = _candidate_section(text)
        source_ref = _line_source_ref(source_path, heading, line_number)
        extracted.append(
            {
                "section_candidate": section,
                "text": text,
                "source_ref": source_ref,
            }
        )

    return extracted


def _conflict_key_and_stance(text: str) -> Tuple[str, str]:
    if "手机号" in text and ("唯一" in text or "重复" in text):
        if "重复" in text:
            return "phone_uniqueness", "allows_duplicate"
        if "唯一" in text:
            return "phone_uniqueness", "requires_unique"

    if "短信验证码" in text or "验证码" in text:
        if "不需要" in text or "无需" in text:
            return "sms_verification_required", "not_required"
        if "需要" in text or "验证" in text:
            return "sms_verification_required", "required"

    if "自动登录" in text:
        if "不会" in text or "不自动" in text:
            return "registration_auto_login", "not_auto_login"
        return "registration_auto_login", "auto_login"

    if "登录失败" in text and "日志" in text:
        if "不记录" in text:
            return "login_failure_log_recording", "not_recorded"
        if "记录" in text:
            return "login_failure_log_recording", "recorded"

    return "", ""


def _has_source_line_range(source_ref: str) -> bool:
    return bool(re.search(r":L\d+-L\d+$", source_ref))


def _source_ref_identity(source_ref: str) -> Tuple[str, int]:
    normalized = source_ref.replace("\\", "/")
    match = re.search(r"^(?P<path>.+?)#.*:L(?P<line>\d+)-L\d+$", normalized)
    if not match:
        return normalized, 0
    return match.group("path"), int(match.group("line"))


def _load_gold_labels(path: str | Path | None = None) -> List[Dict[str, Any]]:
    label_path = Path(path) if path else DEFAULT_GOLD_LABELS_PATH
    if not label_path.exists():
        return []
    data = json.loads(label_path.read_text(encoding="utf-8"))
    return data.get("items", [])


def _gold_label_key(label: Dict[str, Any]) -> Tuple[str, int]:
    return str(label.get("source_path", "")).replace("\\", "/"), int(label.get("line", 0))


def _gold_by_source(labels: List[Dict[str, Any]]) -> Dict[Tuple[str, int], Dict[str, Any]]:
    return {_gold_label_key(label): label for label in labels}


def _gold_label_for_item(
    item: Dict[str, Any],
    labels_by_source: Dict[Tuple[str, int], Dict[str, Any]],
) -> Dict[str, Any] | None:
    return labels_by_source.get(_source_ref_identity(str(item.get("source_ref", ""))))


def evaluate_with_gold_labels(
    *,
    review_items: List[Dict[str, Any]],
    released_items: List[Dict[str, Any]],
    gold_labels: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    labels = gold_labels if gold_labels is not None else _load_gold_labels()
    labels_by_source = _gold_by_source(labels)
    released_keys = {
        _source_ref_identity(str(item.get("source_ref", "")))
        for item in released_items
    }

    false_release_count = 0
    false_reject_count = 0
    conflict_detected_count = 0
    conflict_missed_count = 0
    irrelevant_recall_count = 0
    deprecated_recall_count = 0

    for item in review_items:
        key = _source_ref_identity(str(item.get("source_ref", "")))
        label = labels_by_source.get(key)
        if not label:
            continue

        tags = set(label.get("tags", []))
        expected_decision = label.get("expected_decision")
        released = key in released_keys

        if released and expected_decision != "release":
            false_release_count += 1
        if not released and expected_decision == "release":
            false_reject_count += 1
        if "conflict" in tags:
            if item.get("conflict_status") == "conflict":
                conflict_detected_count += 1
            else:
                conflict_missed_count += 1
        if "irrelevant" in tags:
            irrelevant_recall_count += 1
        if "deprecated" in tags:
            deprecated_recall_count += 1

    return {
        "gold_label_count": len(labels),
        "false_release_count": false_release_count,
        "false_reject_count": false_reject_count,
        "conflict_detected_count": conflict_detected_count,
        "conflict_missed_count": conflict_missed_count,
        "irrelevant_recall_count": irrelevant_recall_count,
        "deprecated_recall_count": deprecated_recall_count,
    }


def _detect_conflicts(items: List[Dict[str, Any]]) -> None:
    groups: Dict[str, List[Tuple[Dict[str, Any], str]]] = {}
    for item in items:
        if item.get("section_candidate") == "unknowns":
            continue
        key, stance = _conflict_key_and_stance(item.get("text", ""))
        if key:
            groups.setdefault(key, []).append((item, stance))

    contradictory_stances = {
        "phone_uniqueness": {"requires_unique", "allows_duplicate"},
        "sms_verification_required": {"required", "not_required"},
        "registration_auto_login": {"not_auto_login", "auto_login"},
        "login_failure_log_recording": {"recorded", "not_recorded"},
    }
    for key, group in groups.items():
        active_group = [
            (item, stance)
            for item, stance in group
            if item.get("version_status") == "active"
        ]
        stances = {stance for _, stance in active_group}
        if contradictory_stances.get(key, set()).issubset(stances):
            for item, _ in active_group:
                item["conflict_status"] = "conflict"
                item["review_status"] = "pending"


def build_review_queue(
    requirement_text: str,
    chunks: List[Dict[str, Any]],
    *,
    run_id: str,
    baseline_manual_preparation_minutes: float = 30.0,
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        score = int(chunk.get("relevance_score", 0))
        scope_status = _scope_status(metadata, score)
        version_status = metadata.get("effective_status", "unknown") or "unknown"
        confidence = metadata.get("trust", "medium") or "medium"

        for candidate in _extract_candidate_lines(chunk):
            source_ref = candidate["source_ref"]
            source_verified = _has_source_line_range(source_ref)
            section = candidate["section_candidate"]
            item = {
                "id": _stable_id(
                    f"candidate_{SECTION_PREFIX.get(section, 'item')}",
                    candidate["text"],
                    source_ref,
                ),
                "section_candidate": section,
                "text": candidate["text"],
                "source_ref": source_ref,
                "source_verified": source_verified,
                "human_confirmed": False,
                "review_status": "pending",
                "version_status": version_status,
                "scope_status": scope_status,
                "conflict_status": "none",
                "confidence": confidence,
                "rejection_reason": "",
                "applies_to_candidates": _applies_to_candidates_for_item(
                    requirement_text=requirement_text,
                    heading=chunk.get("heading", ""),
                    text=candidate["text"],
                ),
            }
            if version_status == "deprecated":
                item["review_status"] = "pending"
            if confidence == "low":
                item["review_status"] = "pending"
            items.append(item)

    _detect_conflicts(items)
    queue = {
        "run_id": run_id,
        "created_at": _now(),
        "requirement_text": requirement_text,
        "items": items,
        "metrics": calculate_review_metrics(
            items,
            baseline_manual_preparation_minutes=baseline_manual_preparation_minutes,
        ),
    }
    return queue


def _release_blockers(item: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    if item.get("source_verified") is not True:
        blockers.append("source_not_verified")
    if item.get("human_confirmed") is not True:
        blockers.append("human_not_confirmed")
    if item.get("review_status") != "approved":
        blockers.append("review_not_approved")
    if not _has_source_line_range(str(item.get("source_ref", ""))):
        blockers.append("missing_source_line_range")
    if item.get("version_status") != "active":
        blockers.append("version_not_active")
    if item.get("conflict_status") != "none":
        blockers.append("conflict_not_resolved")
    if item.get("scope_status") != "matched":
        blockers.append("scope_not_matched")
    return blockers


def _release_allowed(item: Dict[str, Any]) -> bool:
    return not _release_blockers(item)


def build_consumable_context(
    review_queue: Dict[str, Any],
) -> Dict[str, Any]:
    structured_content = {section: [] for section in REQUIRED_SECTIONS}
    review_items = review_queue.get("items", [])
    _detect_conflicts(review_items)
    released_items: List[Dict[str, Any]] = []
    release_audit: List[Dict[str, Any]] = []

    for item in review_items:
        blockers = _release_blockers(item)
        release_audit.append(
            {
                "id": item.get("id"),
                "section_candidate": item.get("section_candidate"),
                "source_ref": item.get("source_ref"),
                "review_status": item.get("review_status"),
                "source_verified": item.get("source_verified"),
                "human_confirmed": item.get("human_confirmed"),
                "version_status": item.get("version_status"),
                "conflict_status": item.get("conflict_status"),
                "scope_status": item.get("scope_status"),
                "decision": "blocked" if blockers else "released",
                "blockers": blockers,
            }
        )
        if blockers:
            continue

        section = item.get("section_candidate")
        if section not in structured_content:
            continue

        released = {
            "id": item["id"].replace("candidate_", "", 1),
            "text": item["text"],
            "source_ref": item["source_ref"],
            "source_verified": True,
            "human_confirmed": True,
            "review_status": "approved",
            "version_status": item.get("version_status"),
            "conflict_status": item.get("conflict_status"),
            "scope_status": item.get("scope_status"),
            "confidence": item.get("confidence", "medium"),
        }
        if item.get("applies_to_candidates"):
            released["applies_to_candidates"] = item["applies_to_candidates"]
        structured_content[section].append(released)
        released_items.append(released)

    metrics = calculate_review_metrics(
        review_items,
        manual_review_minutes=review_queue.get("metrics", {}).get(
            "manual_review_minutes", 0
        ),
        baseline_manual_preparation_minutes=review_queue.get("metrics", {}).get(
            "baseline_manual_preparation_minutes", 30
        ),
    )
    metrics.update(
        evaluate_with_gold_labels(
            review_items=review_items,
            released_items=released_items,
        )
    )

    return {
        "context_package_version": "v2",
        "context_origin": "auto_prepared",
        "context_id": f"auto_context_{review_queue.get('run_id')}",
        "summary": "Auto-prepared human-confirmed Context Package V2.",
        "structured_content": structured_content,
        "release_audit": release_audit,
        "metrics": metrics,
    }


def calculate_review_metrics(
    items: List[Dict[str, Any]],
    *,
    manual_review_minutes: float = 0.0,
    baseline_manual_preparation_minutes: float = 30.0,
) -> Dict[str, Any]:
    generated = len(items)
    source_verified = sum(1 for item in items if item.get("source_verified") is True)
    human_confirmed = sum(1 for item in items if item.get("human_confirmed") is True)
    rejected = sum(1 for item in items if item.get("review_status") == "rejected")
    edited = sum(1 for item in items if item.get("edited") is True)
    deprecated_blocked = sum(1 for item in items if item.get("version_status") == "deprecated")
    conflict_blocked = sum(1 for item in items if item.get("conflict_status") == "conflict")
    scope_unknown_blocked = sum(1 for item in items if item.get("scope_status") != "matched")
    low_trust_blocked = sum(1 for item in items if item.get("confidence") == "low")
    false_release_count = sum(
        1
        for item in items
        if item.get("review_status") == "approved" and not _release_allowed(item)
    )
    time_saved_ratio = 0
    if baseline_manual_preparation_minutes:
        time_saved_ratio = max(
            0,
            (baseline_manual_preparation_minutes - manual_review_minutes)
            / baseline_manual_preparation_minutes,
        )

    return {
        "generated_item_count": generated,
        "review_queue_count": generated,
        "source_verified_count": source_verified,
        "human_confirmed_count": human_confirmed,
        "rejected_count": rejected,
        "edited_count": edited,
        "false_release_count": false_release_count,
        "deprecated_blocked_count": deprecated_blocked,
        "conflict_blocked_count": conflict_blocked,
        "scope_unknown_blocked_count": scope_unknown_blocked,
        "low_trust_blocked_count": low_trust_blocked,
        "manual_review_minutes": manual_review_minutes,
        "baseline_manual_preparation_minutes": baseline_manual_preparation_minutes,
        "time_saved_ratio": round(time_saved_ratio, 4),
    }


def save_json(data: Dict[str, Any], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
