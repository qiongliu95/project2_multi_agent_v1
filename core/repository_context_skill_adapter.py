"""
Adapter for the local repository context External Skill.

This module is the only place that knows how to locate, load, and call the
current understand-domain implementation. Pipeline and Context Provider code
consume the standard Context Package returned here.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


SKILL_ID = "understand_domain_repository_context"
PROVIDER_ID = "understand_domain_repository_context_provider"
CAPABILITY_TYPE = "skill"
DEFAULT_SKILL_SCRIPT_PATH = (
    Path.home()
    / ".codex"
    / "skills"
    / "understand-domain"
    / "extract-domain-context.py"
)
REQUIRED_FUNCTIONS = [
    "parse_gitignore",
    "scan_file_tree",
    "detect_entry_points",
    "extract_file_signatures",
    "extract_metadata",
    "_truncate_to_fit",
]


def _build_error_record(
    *,
    source_id: str,
    error: Exception,
) -> Dict[str, str]:
    return {
        "stage_id": f"context:{source_id}",
        "error_type": type(error).__name__,
        "message": str(error),
    }


def _initial_skill_metadata(
    skill_script_path: Path | None = None,
) -> Dict[str, Any]:
    loaded_path = skill_script_path or DEFAULT_SKILL_SCRIPT_PATH
    return {
        "skill_id": SKILL_ID,
        "declared_source": str(DEFAULT_SKILL_SCRIPT_PATH),
        "loaded_path": str(loaded_path),
        "required_functions": REQUIRED_FUNCTIONS,
        "loaded": False,
    }


def _file_fingerprint(path: Path) -> Dict[str, Any]:
    content = path.read_bytes()
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def _build_failed_package(
    *,
    source_id: str,
    source: Dict[str, Any],
    required: bool,
    error: Exception,
    skill_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    source_payload = dict(source)
    if skill_metadata:
        source_payload["skill_metadata"] = skill_metadata

    return {
        "context_id": source_id,
        "provider_id": PROVIDER_ID,
        "tool_id": None,
        "skill_id": SKILL_ID,
        "capability_type": CAPABILITY_TYPE,
        "source": source_payload,
        "required": required,
        "content_type": source.get("type"),
        "content": None,
        "status": "failed",
        "error": _build_error_record(source_id=source_id, error=error),
    }


def _load_skill_module(
    skill_metadata: Dict[str, Any],
    skill_script_path: Path | None = None,
) -> tuple[Any, Dict[str, Any]]:
    resolved_script_path = skill_script_path or DEFAULT_SKILL_SCRIPT_PATH
    skill_metadata["loaded_path"] = str(resolved_script_path)

    if not resolved_script_path.exists():
        raise FileNotFoundError(
            f"External Skill source not found: {resolved_script_path}"
        )

    skill_metadata["fingerprint"] = _file_fingerprint(resolved_script_path)

    spec = importlib.util.spec_from_file_location(
        "understand_domain_repository_context_skill",
        resolved_script_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load External Skill source: {resolved_script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    missing_functions = [
        function_name
        for function_name in REQUIRED_FUNCTIONS
        if not callable(getattr(module, function_name, None))
    ]
    if missing_functions:
        raise AttributeError(
            "External Skill interface is incompatible. Missing functions: "
            + ", ".join(missing_functions)
        )

    skill_metadata["version"] = getattr(module, "__version__", None)
    skill_metadata["loaded"] = True
    return module, skill_metadata


def build_repository_context_package(
    *,
    source_id: str,
    source: Dict[str, Any],
    repository_root: Path,
    required: bool,
) -> Dict[str, Any]:
    """
    Build a standard Context Package using the repository context Skill.

    All Skill-specific loading, interface validation, function calls, and output
    conversion are intentionally kept inside this adapter.
    """
    skill_metadata: Dict[str, Any] = _initial_skill_metadata()
    try:
        module, skill_metadata = _load_skill_module(skill_metadata)

        gitignore_patterns = module.parse_gitignore(repository_root)
        file_tree = module.scan_file_tree(repository_root, gitignore_patterns)
        entry_points = module.detect_entry_points(repository_root, file_tree)
        file_signatures = module.extract_file_signatures(repository_root, file_tree)
        metadata = module.extract_metadata(repository_root)

        skill_output = {
            "skill_id": SKILL_ID,
            "skill_metadata": skill_metadata,
            "project_root": str(repository_root),
            "file_count": len(file_tree),
            "file_tree": file_tree,
            "entry_points": entry_points,
            "file_signatures": file_signatures,
            "metadata": metadata,
            "safety_profile": {
                "local_only": True,
                "read_only": True,
                "network_access": False,
                "shell_commands": False,
                "writes_to_repository": False,
            },
        }
        skill_output = module._truncate_to_fit(skill_output)

        return {
            "context_id": source_id,
            "provider_id": PROVIDER_ID,
            "tool_id": None,
            "skill_id": SKILL_ID,
            "capability_type": CAPABILITY_TYPE,
            "source": {
                "type": "local_repository",
                "path": str(repository_root),
                "skill_metadata": skill_metadata,
            },
            "required": required,
            "content_type": "repository_context_json",
            "content": json.dumps(skill_output, ensure_ascii=False, indent=2),
            "status": "success",
            "error": None,
        }
    except Exception as error:
        return _build_failed_package(
            source_id=source_id,
            source=source,
            required=required,
            error=error,
            skill_metadata=skill_metadata,
        )
