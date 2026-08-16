"""
运行项目二的 4 Agent 串行工作流。

主要流程：
1. 读取对应的 prompt 模板
2. 构造每个 Agent 的输入
3. 调用模型得到结果
4. 解析 JSON
5. 串行执行 4 个 Agent
6. 保存最终结果到 outputs

设计考虑：
- 当前重点是先跑通最小链路，不追求一次性把 JSON 容错做到很复杂
- 模型偶尔会返回带代码块或解释文字的结果，所以做了最小 JSON 提取
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.llm_client import call_llm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def load_prompt_template(filename: str) -> str:
    """
    读取某个 Agent 的 prompt 模板文件。

    输入：
    - filename：prompt 文件名

    输出：
    - prompt 模板文本
    """
    prompt_path = PROMPTS_DIR / filename
    return prompt_path.read_text(encoding="utf-8")


def extract_json_text(raw_text: str) -> str:
    """
    从模型原始输出中尽量提取 JSON 文本。

    输入：
    - raw_text：模型返回的原始文本

    输出：
    - 提取出的 JSON 字符串
    """
    cleaned_text = raw_text.strip()

    # 先处理模型可能返回的 markdown 代码块包裹
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.removeprefix("```json").strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").strip()
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text.removesuffix("```").strip()

    # 再从文本中截取最外层 JSON 对象
    start_index = cleaned_text.find("{")
    end_index = cleaned_text.rfind("}")

    if start_index == -1 or end_index == -1 or end_index <= start_index:
        raise ValueError("模型输出中未找到有效 JSON。")

    return cleaned_text[start_index : end_index + 1]


def parse_json_result(raw_text: str) -> dict[str, Any]:
    """
    把模型文本结果解析成字典。

    输入：
    - raw_text：模型原始输出文本

    输出：
    - 解析后的 JSON 字典
    """
    json_text = extract_json_text(raw_text)
    return json.loads(json_text)


def build_agent_1_prompt(requirement_text: str) -> str:
    """
    构造 Agent 1 的完整 prompt。

    输入：
    - requirement_text：原始需求文本

    输出：
    - Agent 1 的完整 prompt
    """
    prompt_template = load_prompt_template("agent_1_requirement_analysis.md")

    return (
        f"{prompt_template}\n\n"
        f"【原始需求文本】\n"
        f"{requirement_text}"
    )


def build_agent_2_prompt(
    requirement_text: str,
    agent_1_result: dict[str, Any],
) -> str:
    """
    构造 Agent 2 的完整 prompt。

    输入：
    - requirement_text：原始需求文本
    - agent_1_result：Agent 1 输出结果

    输出：
    - Agent 2 的完整 prompt
    """
    prompt_template = load_prompt_template("agent_2_risk_review.md")
    agent_1_json = json.dumps(agent_1_result, ensure_ascii=False, indent=2)

    return (
        f"{prompt_template}\n\n"
        f"【原始需求文本】\n"
        f"{requirement_text}\n\n"
        f"【需求解析结果】\n"
        f"{agent_1_json}"
    )


def build_agent_3_prompt(
    requirement_text: str,
    agent_1_result: dict[str, Any],
    agent_2_result: dict[str, Any],
) -> str:
    """
    构造 Agent 3 的完整 prompt。

    输入：
    - requirement_text：原始需求文本
    - agent_1_result：Agent 1 输出结果
    - agent_2_result：Agent 2 输出结果

    输出：
    - Agent 3 的完整 prompt
    """
    prompt_template = load_prompt_template("agent_3_test_design.md")
    agent_1_json = json.dumps(agent_1_result, ensure_ascii=False, indent=2)
    agent_2_json = json.dumps(agent_2_result, ensure_ascii=False, indent=2)

    return (
        f"{prompt_template}\n\n"
        f"【原始需求文本】\n"
        f"{requirement_text}\n\n"
        f"【需求解析结果】\n"
        f"{agent_1_json}\n\n"
        f"【风险审查结果】\n"
        f"{agent_2_json}"
    )


def build_agent_4_prompt(
    agent_1_result: dict[str, Any],
    agent_2_result: dict[str, Any],
    agent_3_result: dict[str, Any],
) -> str:
    """
    构造 Agent 4 的完整 prompt。

    输入：
    - agent_1_result：Agent 1 输出结果
    - agent_2_result：Agent 2 输出结果
    - agent_3_result：Agent 3 输出结果

    输出：
    - Agent 4 的完整 prompt
    """
    prompt_template = load_prompt_template("agent_4_summary.md")
    agent_1_json = json.dumps(agent_1_result, ensure_ascii=False, indent=2)
    agent_2_json = json.dumps(agent_2_result, ensure_ascii=False, indent=2)
    agent_3_json = json.dumps(agent_3_result, ensure_ascii=False, indent=2)

    return (
        f"{prompt_template}\n\n"
        f"【需求解析结果】\n"
        f"{agent_1_json}\n\n"
        f"【风险审查结果】\n"
        f"{agent_2_json}\n\n"
        f"【测试设计结果】\n"
        f"{agent_3_json}"
    )


def run_agent_1(requirement_text: str) -> dict[str, Any]:
    """
    执行 Agent 1：需求解析。

    输入：
    - requirement_text：原始需求文本

    输出：
    - Agent 1 的结构化结果
    """
    prompt_text = build_agent_1_prompt(requirement_text)
    raw_result = call_llm(prompt_text)
    return parse_json_result(raw_result)


def run_agent_2(
    requirement_text: str,
    agent_1_result: dict[str, Any],
) -> dict[str, Any]:
    """
    执行 Agent 2：风险审查。

    输入：
    - requirement_text：原始需求文本
    - agent_1_result：Agent 1 输出结果

    输出：
    - Agent 2 的结构化结果
    """
    prompt_text = build_agent_2_prompt(requirement_text, agent_1_result)
    raw_result = call_llm(prompt_text)
    return parse_json_result(raw_result)


def run_agent_3(
    requirement_text: str,
    agent_1_result: dict[str, Any],
    agent_2_result: dict[str, Any],
) -> dict[str, Any]:
    """
    执行 Agent 3：测试设计。

    输入：
    - requirement_text：原始需求文本
    - agent_1_result：Agent 1 输出结果
    - agent_2_result：Agent 2 输出结果

    输出：
    - Agent 3 的结构化结果
    """
    prompt_text = build_agent_3_prompt(
        requirement_text=requirement_text,
        agent_1_result=agent_1_result,
        agent_2_result=agent_2_result,
    )
    raw_result = call_llm(prompt_text)
    return parse_json_result(raw_result)


def run_agent_4(
    agent_1_result: dict[str, Any],
    agent_2_result: dict[str, Any],
    agent_3_result: dict[str, Any],
) -> dict[str, Any]:
    """
    执行 Agent 4：结果汇总。

    输入：
    - agent_1_result：Agent 1 输出结果
    - agent_2_result：Agent 2 输出结果
    - agent_3_result：Agent 3 输出结果

    输出：
    - Agent 4 的结构化结果
    """
    prompt_text = build_agent_4_prompt(
        agent_1_result=agent_1_result,
        agent_2_result=agent_2_result,
        agent_3_result=agent_3_result,
    )
    raw_result = call_llm(prompt_text)
    return parse_json_result(raw_result)


def save_pipeline_result(
    pipeline_result: dict[str, Any],
    output_filename: str = "pipeline_result.json",
) -> None:
    """
    保存完整流水线结果到 outputs 目录。

    输入：
    - pipeline_result：完整工作流结果
    - output_filename：输出文件名

    输出：
    - 无，直接写入文件
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / output_filename

    output_path.write_text(
        json.dumps(pipeline_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_pipeline(requirement_text: str) -> dict[str, Any]:
    """
    运行完整 4 Agent 串行工作流。

    输入：
    - requirement_text：原始需求文本

    输出：
    - 包含 4 个 Agent 结果的完整字典
    """
    # 先跑需求解析，得到后续步骤的基础输入
    agent_1_result = run_agent_1(requirement_text)

    # 再基于原始需求 + 需求解析结果做风险识别
    agent_2_result = run_agent_2(requirement_text, agent_1_result)

    # 再把前两步结果转成测试设计内容
    agent_3_result = run_agent_3(
        requirement_text=requirement_text,
        agent_1_result=agent_1_result,
        agent_2_result=agent_2_result,
    )

    # 最后收口，形成最终汇总结果
    agent_4_result = run_agent_4(
        agent_1_result=agent_1_result,
        agent_2_result=agent_2_result,
        agent_3_result=agent_3_result,
    )

    full_result = {
        "requirement_text": requirement_text,
        "agent_1_requirement_parsing": agent_1_result,
        "agent_2_risk_analysis": agent_2_result,
        "agent_3_test_design": agent_3_result,
        "agent_4_result_summary": agent_4_result,
    }

    save_pipeline_result(full_result)
    return full_result