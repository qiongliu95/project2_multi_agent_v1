"""
Agent1 两阶段扩展中的问题决策模块。

作用：
- 基于 requirement_text 和 Agent1 基础解析结果
- 单独生成 open_questions
- 作为 Agent1 两阶段版本的第二步

主要流程：
1. 读取问题决策 Prompt
2. 组织 requirement_text 和 parsing_result 作为输入
3. 调用模型
4. 解析并返回 JSON 结果

设计考虑：
- 这是扩展模块，不影响 baseline Agent1
- 只在 config 开启 use_agent1_two_stage 时生效
- 输出应保持最小结构，只包含 open_questions
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
    project_root = Path(__file__).resolve().parent.parent.parent
    full_path = project_root / prompt_path
    return full_path.read_text(encoding="utf-8")


def parse_json_result(raw_text: str) -> Dict[str, Any]:
    """
    将模型输出解析为 JSON 字典。

    输入：
    - raw_text: 模型原始输出

    输出：
    - 解析后的字典
    """
    try:
        return json.loads(raw_text)
    except Exception:
        print("Agent1 Question Decision 返回非标准 JSON：")
        print(raw_text)
        raise


def run_agent1_question_decision(
    requirement_text: str,
    parsing_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    执行 Agent1 两阶段中的问题决策。

    输入：
    - requirement_text: 原始需求文本
    - parsing_result: Agent1 基础解析结果

    输出：
    - 仅包含 open_questions 的结果字典
    """
    prompt = load_prompt(
        "prompts/extensions/agent1_two_stage/prompts/agent1_question_decision.md"
    )

    # 把需求原文和结构化解析结果一起交给问题决策模块
    payload = {
        "requirement_text": requirement_text,
        "agent_1_requirement_parsing": parsing_result,
    }

    raw_result = call_llm(prompt, payload)
    result = parse_json_result(raw_result)

    # 兜底：如果字段缺失，则回退到 parsing 阶段问题
    if "open_questions" not in result:
        result["open_questions"] = parsing_result.get("open_questions", [])

    # 兜底：如果错误地收缩为空，但 parsing 原本有问题，则回退
    if not result["open_questions"] and parsing_result.get("open_questions"):
        result["open_questions"] = parsing_result.get("open_questions", [])

    return result