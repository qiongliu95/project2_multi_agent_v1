"""
Agent1 基础解析模块。

作用：
- 调用 baseline 的 Requirement Parsing Prompt
- 返回结构化需求解析结果

主要流程：
1. 读取 prompt
2. 调用模型
3. 解析 JSON
4. 返回结果

设计考虑：
- 当前先保留最小骨架
- 模型调用函数可后续接入你现有 API 封装
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


def run_agent1_parsing(requirement_text: str) -> Dict[str, Any]:
    """
    执行 Agent1 基础解析。
    """
    prompt = load_prompt("prompts/agent_1_requirement_analysis.md")

    payload = {
        "requirement_text": requirement_text
    }

    raw_result = call_llm(prompt, payload)

    return parse_json_result(raw_result)