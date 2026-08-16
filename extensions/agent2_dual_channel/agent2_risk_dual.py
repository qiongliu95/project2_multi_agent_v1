"""
Agent2 双通道风险分析模块。

作用：
- 输出 strict_risks（主链路使用）
- 输出 advisory_considerations（扩展参考）

注意：
- 当前不接入主 pipeline
- 仅用于扩展验证
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.llm_client import call_llm


def load_prompt(prompt_path: str) -> str:
    project_root = Path(__file__).resolve().parent.parent.parent
    full_path = project_root / prompt_path
    return full_path.read_text(encoding="utf-8")


def parse_json_result(raw_text: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_text)
    except Exception:
        print("Agent2 Dual 返回异常：")
        print(raw_text)
        raise


def run_agent2_risk_dual(
    requirement_text: str,
    parsing_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    执行双通道风险分析。

    输入：
    - requirement_text
    - parsing_result

    输出：
    - strict_risks + advisory_considerations
    """
    prompt = load_prompt(
        "prompts/extensions/agent2_dual_channel/prompts/agent2_risk_dual.md"
    )

    payload = {
        "requirement_text": requirement_text,
        "agent_1_requirement_parsing": parsing_result,
    }

    raw_result = call_llm(prompt, payload)
    result = parse_json_result(raw_result)

    # 最小兜底
    if "strict_risks" not in result:
        result["strict_risks"] = {}

    if "advisory_considerations" not in result:
        result["advisory_considerations"] = []

    return result