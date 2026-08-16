"""
Agent4 结果汇总模块。

作用：
- 汇总需求解析、风险分析和测试设计结果
- 输出最终面向阅读的摘要

主要流程：
1. 读取 prompt
2. 组织上下文
3. 调用模型
4. 解析 JSON

设计考虑：
- 主链路只汇总严格风险
- advisory 信息如需展示，可后续单独挂载
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from core.llm_client import call_llm


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


def run_agent4_summary(
    requirement_text: str,
    parsing_result: Dict[str, Any],
    strict_risks: Dict[str, Any],
    test_result: Dict[str, Any],
    question_result: Dict[str, Any],
    full_risk_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    执行 Agent4 汇总。

    输入：
    - requirement_text: 原始需求文本
    - parsing_result: Agent1 解析结果
    - strict_risks: Agent2 严格风险结果
    - test_result: Agent3 结果
    - question_result: Agent1 问题结果
    - full_risk_result: Agent2 完整结果

    输出：
    - Agent4 汇总结果
    """
    prompt = load_prompt("prompts/agent_4_summary.md")
    payload = {
        "requirement_text": requirement_text,
        "agent_1_requirement_parsing": parsing_result,
        "agent_1_questions": question_result,
        "agent_2_risk_analysis": strict_risks,
        "agent_3_test_design": test_result,
        "agent_2_full_output": full_risk_result,
    }
    raw_result = call_llm(prompt, payload)
    return parse_json_result(raw_result)