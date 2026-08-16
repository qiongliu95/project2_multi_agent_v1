"""
Compile a human-maintained business context document into Context Package V2.

The compiler is deterministic: it parses a small Markdown template, validates
required fields, generates stable IDs/source refs, and emits the existing
runtime schema consumed by local_structured_context.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_METADATA = [
    "module_id",
    "module_name",
    "version",
    "status",
    "effective_date",
    "owner",
]

REQUIRED_SECTIONS = [
    "功能目标",
    "业务对象",
    "用户角色",
    "主流程",
    "业务规则",
    "限制条件",
    "未确认事项",
]

CONTEXT_SECTIONS = [
    "confirmed_facts",
    "business_rules",
    "constraints",
    "process_flows",
    "unknowns",
    "source_refs",
    "quality_flags",
]

SECTION_TO_RUNTIME = {
    "功能目标": ("confirmed_facts", "fact"),
    "业务对象": ("confirmed_facts", "fact"),
    "用户角色": ("confirmed_facts", "fact"),
    "前置条件": ("business_rules", "rule"),
    "主流程": ("process_flows", "flow"),
    "业务规则": ("business_rules", "rule"),
    "限制条件": ("constraints", "constraint"),
    "已定义异常处理": ("business_rules", "rule"),
    "异常场景": ("business_rules", "rule"),
    "风险关注点": ("quality_flags", "quality"),
    "历史问题": ("quality_flags", "quality"),
    "验证关注点": ("quality_flags", "quality"),
    "未确认事项": ("unknowns", "unknown"),
}


def _now() -> str:
    return datetime.now().isoformat()


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _stable_id(prefix: str, text: str, source_ref: str) -> str:
    digest = hashlib.md5(f"{text}|{source_ref}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _parse_frontmatter(lines: List[str]) -> Tuple[Dict[str, str], int]:
    metadata: Dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return metadata, 0

    for index, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if stripped == "---":
            return metadata, index
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, 0


def _clean_list_item(line: str) -> str:
    text = line.strip()
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^\d+[.)、]\s*", "", text)
    return text.strip()


def _split_inline_values(value: str) -> List[str]:
    return [
        item.strip()
        for item in re.split(r"[;；]", value)
        if item.strip()
    ]


def _parse_list_item(line: str) -> Dict[str, Any]:
    """
    Parse one human-maintained list item.

    Optional inline attributes:
    - text | applies_to: action one; action two
    - text | applies_to_candidates: action one; action two
    """
    text = _clean_list_item(line)
    if not text:
        return {"text": ""}

    parts = [part.strip() for part in text.split("|")]
    parsed: Dict[str, Any] = {"text": parts[0].strip()}

    for raw_attribute in parts[1:]:
        if not raw_attribute:
            continue
        if ":" in raw_attribute:
            key, value = raw_attribute.split(":", 1)
        elif "=" in raw_attribute:
            key, value = raw_attribute.split("=", 1)
        else:
            continue

        normalized_key = key.strip()
        if normalized_key in {"applies_to", "applies_to_candidates"}:
            parsed[normalized_key] = _split_inline_values(value)

    return parsed


def _parse_sections(lines: List[str], start_line: int) -> Dict[str, List[Dict[str, Any]]]:
    sections: Dict[str, List[Dict[str, Any]]] = {}
    current_section = ""

    for line_number, raw_line in enumerate(lines, start=1):
        if line_number <= start_line:
            continue

        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current_section = stripped.lstrip("#").strip()
            sections.setdefault(current_section, [])
            continue

        if not current_section:
            continue

        parsed_item = _parse_list_item(raw_line)
        text = parsed_item.get("text", "")
        if not text or text == "---" or text.startswith("#"):
            continue
        parsed_item["line"] = line_number
        sections.setdefault(current_section, []).append(
            parsed_item
        )

    return sections


def _validate(metadata: Dict[str, str], sections: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    errors: List[str] = []
    for key in REQUIRED_METADATA:
        if not metadata.get(key):
            errors.append(f"missing metadata: {key}")

    status = metadata.get("status")
    if status and status != "active":
        errors.append("only active human context can be compiled")

    for section in REQUIRED_SECTIONS:
        if not sections.get(section):
            errors.append(f"missing or empty section: {section}")

    return errors


def _source_ref(path: Path, section: str, line_number: int) -> str:
    return f"{_rel_path(path)}#{section}:L{line_number}-L{line_number}"


def _runtime_item(
    *,
    path: Path,
    section: str,
    prefix: str,
    entry: Dict[str, Any],
    metadata: Dict[str, str],
) -> Dict[str, Any]:
    source_ref = _source_ref(path, section, int(entry["line"]))
    text = str(entry["text"])
    item = {
        "id": _stable_id(prefix, text, source_ref),
        "text": text,
        "source_ref": source_ref,
        "confidence": "high",
        "source_verified": True,
        "human_confirmed": True,
        "review_status": "approved",
        "version_status": metadata.get("status", "active"),
        "scope_status": "matched",
    }
    for key in ["applies_to", "applies_to_candidates"]:
        values = entry.get(key)
        if isinstance(values, list) and values:
            item[key] = values
    return item


def compile_human_context_file(path: str | Path) -> Dict[str, Any]:
    input_path = Path(path)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    lines = input_path.read_text(encoding="utf-8").splitlines()
    metadata, frontmatter_end = _parse_frontmatter(lines)
    sections = _parse_sections(lines, frontmatter_end)
    errors = _validate(metadata, sections)
    if errors:
        raise ValueError("; ".join(errors))

    structured_content: Dict[str, List[Dict[str, Any]]] = {
        section: [] for section in CONTEXT_SECTIONS
    }
    source_refs: Dict[str, Dict[str, Any]] = {}

    for section, entries in sections.items():
        mapping = SECTION_TO_RUNTIME.get(section)
        if not mapping:
            continue
        runtime_section, prefix = mapping
        for entry in entries:
            item = _runtime_item(
                path=input_path,
                section=section,
                prefix=prefix,
                entry=entry,
                metadata=metadata,
            )
            structured_content[runtime_section].append(item)
            source_refs[item["source_ref"]] = {
                "id": _stable_id("source", item["source_ref"], item["source_ref"]),
                "text": item["source_ref"],
                "source_ref": item["source_ref"],
                "confidence": "high",
            }

    structured_content["source_refs"] = list(source_refs.values())

    context_id = (
        f"compiled_{metadata['module_id']}_{metadata['version']}"
        .replace(".", "_")
        .replace("-", "_")
    )
    return {
        "context_package_version": "v2",
        "context_origin": "human_compiled",
        "context_id": context_id,
        "summary": f"Compiled human-maintained context for {metadata['module_name']}.",
        "metadata": metadata,
        "structured_content": structured_content,
        "compiler_metadata": {
            "compiler": "local_human_context_compiler_v1",
            "compiled_at": _now(),
            "source_path": _rel_path(input_path),
            "required_sections": REQUIRED_SECTIONS,
            "supported_inline_attributes": [
                "applies_to",
                "applies_to_candidates",
            ],
        },
    }


def save_compiled_context(package: Dict[str, Any], path: str | Path) -> Path:
    output_path = Path(path)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
