"""
Agent3 测试设计模块。

作用：
- 基于需求、Agent1 和严格风险结果生成测试设计输出

主要流程：
1. 读取 prompt
2. 组织输入
3. 调用模型
4. 解析 JSON

设计考虑：
- 只读取 strict_risks，不读取 advisory 信息
- 保持主链路可控
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


def run_agent3_test(
    requirement_text: str,
    parsing_result: Dict[str, Any],
    strict_risks: Dict[str, Any],
) -> Dict[str, Any]:
    """
    执行 Agent3 测试设计。

    输入：
    - requirement_text: 原始需求文本
    - parsing_result: Agent1 解析结果
    - strict_risks: Agent2 严格风险结果

    输出：
    - Agent3 测试设计结果
    """
    prompt = load_prompt("prompts/agent_3_test_design.md")
    payload = {
        "requirement_text": requirement_text,
        "agent_1_requirement_parsing": parsing_result,
        "agent_2_risk_analysis": strict_risks,
    }
    raw_result = call_llm(prompt, payload)
    return parse_json_result(raw_result)