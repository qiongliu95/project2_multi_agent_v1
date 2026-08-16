"""
Prepare local historical context for the existing Multi-Agent Workflow.

This entry point intentionally stops before the business Agents. Automatic
indexing and retrieval only create a review queue. A consumable Context Package
V2 is built only from items that were explicitly approved.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.context_preparer import (
    PROJECT_ROOT,
    build_consumable_context,
    build_context_index,
    build_review_queue,
    calculate_review_metrics,
    evaluate_with_gold_labels,
    load_json,
    retrieve_context_candidates,
    save_json,
)


DEFAULT_REQUIREMENT_TEXT = (
    "\u7528\u6237\u53ef\u4ee5\u901a\u8fc7\u624b\u673a\u53f7"
    "\u6ce8\u518c\u8d26\u53f7\uff0c\u6ce8\u518c\u540e\u53ef"
    "\u4ee5\u767b\u5f55\u7cfb\u7edf\uff0c\u5e76\u652f\u6301"
    "\u67e5\u770b\u548c\u4fee\u6539\u81ea\u5df1\u7684"
    "\u4e2a\u4eba\u8d44\u6599\uff0c\u540c\u65f6\u7cfb\u7edf"
    "\u9700\u8bb0\u5f55\u7528\u6237\u64cd\u4f5c\u65e5\u5fd7\u3002"
)


def _new_run_id(prefix: str = "context") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def _resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _output_path(kind: str, run_id: str) -> Path:
    return PROJECT_ROOT / "outputs" / kind / f"{run_id}.json"


def _dump_summary(title: str, data: Dict[str, Any], path: Path) -> None:
    print(title)
    print(f"path: {path}")
    if data.get("run_id"):
        print(f"run_id: {data.get('run_id')}")
    if "documents" in data:
        print(f"documents: {len(data.get('documents') or [])}")
    if "chunks" in data:
        print(f"chunks: {len(data.get('chunks') or [])}")
    if "items" in data:
        print(f"review_queue_items: {len(data.get('items') or [])}")
    if "metrics" in data:
        print("metrics:")
        print(json.dumps(data["metrics"], ensure_ascii=False, indent=2))


def _eligible_for_review_approval(item: Dict[str, Any]) -> bool:
    return (
        item.get("source_verified") is True
        and item.get("version_status") == "active"
        and item.get("conflict_status") == "none"
        and item.get("scope_status") == "matched"
        and item.get("confidence") != "low"
    )


def _split_ids(values: Iterable[str] | None) -> set[str]:
    ids: set[str] = set()
    for value in values or []:
        for item in value.split(","):
            stripped = item.strip()
            if stripped:
                ids.add(stripped)
    return ids


def _interactive_review(queue: Dict[str, Any]) -> None:
    print("Interactive review mode. Candidate content is not released unless approved.")
    print("Use a=approve, r=reject, e=edit+approve, s=skip.")
    for item in queue.get("items", []):
        print("")
        print(f"id: {item.get('id')}")
        print(f"section_candidate: {item.get('section_candidate')}")
        print(f"text: {item.get('text')}")
        print(f"source_ref: {item.get('source_ref')}")
        print(
            "status: "
            f"version={item.get('version_status')}, "
            f"scope={item.get('scope_status')}, "
            f"conflict={item.get('conflict_status')}, "
            f"confidence={item.get('confidence')}"
        )
        choice = input("review [a/r/e/s]: ").strip().lower()
        if choice == "a":
            if _eligible_for_review_approval(item):
                item["human_confirmed"] = True
                item["review_status"] = "approved"
                item["rejection_reason"] = ""
            else:
                item["human_confirmed"] = False
                item["review_status"] = "rejected"
                item["rejection_reason"] = "blocked_by_release_rules"
        elif choice == "r":
            item["human_confirmed"] = False
            item["review_status"] = "rejected"
            reason = input("rejection reason: ").strip()
            item["rejection_reason"] = reason or "manual_reject"
        elif choice == "e":
            edited_text = input("edited text: ").strip()
            if edited_text and _eligible_for_review_approval(item):
                item["text"] = edited_text
                item["edited"] = True
                item["human_confirmed"] = True
                item["review_status"] = "approved"
                item["rejection_reason"] = ""
            else:
                item["human_confirmed"] = False
                item["review_status"] = "rejected"
                item["rejection_reason"] = "edit_empty_or_blocked_by_release_rules"


def command_index(args: argparse.Namespace) -> int:
    run_id = args.run_id or _new_run_id("context_index")
    index = build_context_index(args.source_dir, run_id=run_id)
    output_path = save_json(index, _output_path("context_index", run_id))
    _dump_summary("Historical Context Index", index, output_path)
    return 0


def command_prepare(args: argparse.Namespace) -> int:
    run_id = args.run_id or _new_run_id("context_prepare")
    if args.index:
        index = load_json(_resolve_path(args.index))
    else:
        index = build_context_index(args.source_dir, run_id=run_id)
        save_json(index, _output_path("context_index", run_id))

    chunks = retrieve_context_candidates(
        args.requirement_text,
        index,
        top_k=args.top_k,
    )
    queue = build_review_queue(
        args.requirement_text,
        chunks,
        run_id=run_id,
        baseline_manual_preparation_minutes=args.baseline_manual_preparation_minutes,
    )
    output_path = save_json(queue, _output_path("context_review_queue", run_id))
    _dump_summary("Context Review Queue", queue, output_path)
    return 0


def command_review(args: argparse.Namespace) -> int:
    queue_path = _resolve_path(args.queue)
    queue = load_json(queue_path)
    approve_ids = _split_ids(args.approve_ids)
    reject_ids = _split_ids(args.reject_ids)

    if not args.approve_all_eligible and not approve_ids and not reject_ids:
        _interactive_review(queue)

    for item in queue.get("items", []):
        item_id = item.get("id")
        should_approve = item_id in approve_ids or (
            args.approve_all_eligible and _eligible_for_review_approval(item)
        )
        should_reject = item_id in reject_ids

        if should_reject:
            item["human_confirmed"] = False
            item["review_status"] = "rejected"
            item["rejection_reason"] = args.rejection_reason or "manual_reject"
        elif should_approve:
            item["human_confirmed"] = True
            item["review_status"] = "approved"
            item["rejection_reason"] = ""

    queue["metrics"] = calculate_review_metrics(
        queue.get("items", []),
        manual_review_minutes=args.manual_review_minutes,
        baseline_manual_preparation_minutes=args.baseline_manual_preparation_minutes,
    )
    save_json(queue, queue_path)
    _dump_summary("Reviewed Context Queue", queue, queue_path)
    return 0


def command_build(args: argparse.Namespace) -> int:
    queue = load_json(_resolve_path(args.queue))
    consumable = build_consumable_context(queue)
    output_path = (
        _resolve_path(args.output)
        if args.output
        else _output_path("consumable_context", queue.get("run_id", _new_run_id()))
    )
    save_json(consumable, output_path)
    _dump_summary("Consumable Context Package V2", consumable, output_path)
    return 0


def _flatten_context_items(package: Dict[str, Any]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for section, items in package.get("structured_content", {}).items():
        for item in items:
            copied = dict(item)
            copied["section"] = section
            flattened.append(copied)
    return flattened


def _normalize_for_compare(text: str) -> str:
    normalized = str(text or "").lower()
    for char in " ，。、；;:：,.()（）[]【】 \t\r\n":
        normalized = normalized.replace(char, "")
    return normalized


def _semantic_overlap(left: str, right: str) -> bool:
    left_norm = _normalize_for_compare(left)
    right_norm = _normalize_for_compare(right)
    if not left_norm or not right_norm:
        return False
    if left_norm in right_norm or right_norm in left_norm:
        return True
    if ("未确定" in left) != ("未确定" in right):
        return False
    key_markers = [
        "手机号",
        "唯一",
        "短信验证码",
        "验证码验证",
        "自动登录",
        "登录流程",
        "重新进入登录流程",
        "密码登录",
        "手机号和密码",
        "资料",
        "昵称",
        "头像",
        "注册时间",
        "手机号不可",
        "直接修改",
        "操作日志",
        "日志字段",
        "用户ID",
        "操作类型",
        "结果状态",
        "登录失败",
        "保存周期",
    ]
    left_hits = {marker for marker in key_markers if marker in left}
    right_hits = {marker for marker in key_markers if marker in right}
    return len(left_hits & right_hits) >= 2


def _diff_manual_and_auto(
    *,
    manual_package: Dict[str, Any],
    review_queue: Dict[str, Any],
    consumable_package: Dict[str, Any],
) -> List[Dict[str, Any]]:
    manual_items = _flatten_context_items(manual_package)
    released_items = _flatten_context_items(consumable_package)
    queue_items = review_queue.get("items", [])
    diff_items: List[Dict[str, Any]] = []

    for manual in manual_items:
        exact = [
            item for item in released_items
            if item.get("section") == manual.get("section")
            and _normalize_for_compare(item.get("text", "")) == _normalize_for_compare(manual.get("text", ""))
        ]
        semantic = [
            item for item in released_items
            if item.get("section") == manual.get("section")
            and _semantic_overlap(item.get("text", ""), manual.get("text", ""))
        ]
        queued = [
            item for item in queue_items
            if _semantic_overlap(item.get("text", ""), manual.get("text", ""))
        ]
        misclassified = [
            item for item in released_items
            if item.get("section") != manual.get("section")
            and _semantic_overlap(item.get("text", ""), manual.get("text", ""))
        ]

        if exact:
            status = "exact_match"
        elif semantic:
            status = "semantic_match"
        elif queued and any(item.get("conflict_status") == "conflict" for item in queued):
            status = "conflicting_rule"
        elif misclassified:
            status = "misclassified"
        elif queued:
            status = "missing"
        else:
            status = "missing"

        diff_items.append(
            {
                "manual_id": manual.get("id"),
                "manual_section": manual.get("section"),
                "manual_text": manual.get("text"),
                "status": status,
                "matched_auto_ids": [
                    item.get("id") for item in exact or semantic or misclassified
                ],
                "queued_candidate_ids": [item.get("id") for item in queued],
            }
        )

    for item in queue_items:
        if str(item.get("text", "")).lower().startswith("applies_to:"):
            diff_items.append(
                {
                    "auto_candidate_id": item.get("id"),
                    "auto_text": item.get("text"),
                    "status": "metadata_noise",
                }
            )

    for item in released_items:
        if not any(
            _semantic_overlap(item.get("text", ""), manual.get("text", ""))
            for manual in manual_items
        ):
            diff_items.append(
                {
                    "auto_id": item.get("id"),
                    "auto_section": item.get("section"),
                    "auto_text": item.get("text"),
                    "status": "valid_new_rule",
                }
            )

    return diff_items


def command_evaluate(args: argparse.Namespace) -> int:
    manual = load_json(_resolve_path(args.manual_context))
    queue = load_json(_resolve_path(args.queue))
    consumable = load_json(_resolve_path(args.consumable_context))
    released_items = _flatten_context_items(consumable)
    gold_metrics = evaluate_with_gold_labels(
        review_items=queue.get("items", []),
        released_items=released_items,
    )
    diff_items = _diff_manual_and_auto(
        manual_package=manual,
        review_queue=queue,
        consumable_package=consumable,
    )
    report = {
        "run_id": queue.get("run_id"),
        "gold_metrics": gold_metrics,
        "diff_summary": {
            status: sum(1 for item in diff_items if item.get("status") == status)
            for status in [
                "exact_match",
                "semantic_match",
                "missing",
                "misclassified",
                "metadata_noise",
                "conflicting_rule",
                "valid_new_rule",
            ]
        },
        "diff_items": diff_items,
    }
    output_path = (
        _resolve_path(args.output)
        if args.output
        else PROJECT_ROOT / "outputs" / "context_eval" / f"{queue.get('run_id')}.json"
    )
    save_json(report, output_path)
    _dump_summary("Context Quality Evaluation", report, output_path)
    print("gold_metrics:")
    print(json.dumps(gold_metrics, ensure_ascii=False, indent=2))
    print("diff_summary:")
    print(json.dumps(report["diff_summary"], ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare reviewable local context for the workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Build local history index.")
    index_parser.add_argument("--source-dir", default="data/history")
    index_parser.add_argument("--run-id")
    index_parser.set_defaults(func=command_index)

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Retrieve candidates and create a review queue.",
    )
    prepare_parser.add_argument("--source-dir", default="data/history")
    prepare_parser.add_argument("--index")
    prepare_parser.add_argument("--run-id")
    prepare_parser.add_argument("--top-k", type=int, default=12)
    prepare_parser.add_argument(
        "--requirement-text",
        default=DEFAULT_REQUIREMENT_TEXT,
    )
    prepare_parser.add_argument(
        "--baseline-manual-preparation-minutes",
        type=float,
        default=30.0,
    )
    prepare_parser.set_defaults(func=command_prepare)

    review_parser = subparsers.add_parser(
        "review",
        help="Review queue items without hand-writing Context JSON.",
    )
    review_parser.add_argument("--queue", required=True)
    review_parser.add_argument("--approve-all-eligible", action="store_true")
    review_parser.add_argument("--approve-ids", action="append")
    review_parser.add_argument("--reject-ids", action="append")
    review_parser.add_argument("--rejection-reason", default="")
    review_parser.add_argument("--manual-review-minutes", type=float, default=0.0)
    review_parser.add_argument(
        "--baseline-manual-preparation-minutes",
        type=float,
        default=30.0,
    )
    review_parser.set_defaults(func=command_review)

    build_parser_ = subparsers.add_parser(
        "build",
        help="Build consumable Context Package V2 from approved items.",
    )
    build_parser_.add_argument("--queue", required=True)
    build_parser_.add_argument("--output")
    build_parser_.set_defaults(func=command_build)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Compare manual and auto context and compute gold-label metrics.",
    )
    evaluate_parser.add_argument(
        "--manual-context",
        default="data/context/registration_context_v2.json",
    )
    evaluate_parser.add_argument("--queue", required=True)
    evaluate_parser.add_argument("--consumable-context", required=True)
    evaluate_parser.add_argument("--output")
    evaluate_parser.set_defaults(func=command_evaluate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
