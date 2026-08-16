"""
Harness 统一运行入口。

作用：
- 读取配置、加载测试用例、执行 pipeline，并保存结果。

主要流程：
1. 读取 pipeline_config.json
2. 根据配置计算 run_mode
3. 生成本次运行唯一 run_id
4. 加载 data/test_cases 下的 case
5. 逐个执行 pipeline 并保存结果

设计考虑：
- 这是 Harness 批量运行入口，不替代现有单脚本调试方式
- 当前只支持 baseline 和 agent1_two_stage 两种模式
- run_id 必须在一次运行开始时只生成一次，保证同批 case 落在同一目录
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.pipeline_runner import run_pipeline_with_state
from extensions.harness.case_loader import load_cases
from extensions.harness.result_saver import save_result


def load_config(config_path: str | Path) -> Dict[str, Any]:
    """
    读取运行配置。

    输入：
    - config_path: 配置文件路径

    输出：
    - 配置字典
    """
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_run_mode(config: Dict[str, Any]) -> str:
    """
    根据配置判断当前运行模式。

    输入：
    - config: 配置字典

    输出：
    - run_mode 字符串
    """
    if config.get("use_agent1_two_stage", False):
        return "agent1_two_stage"

    return "baseline"


def build_run_id(run_mode: str) -> str:
    """
    生成本次运行唯一标识。

    输入：
    - run_mode: 当前运行模式

    输出：
    - run_id 字符串
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{run_mode}_{timestamp}"


def main() -> None:
    """
    执行 Harness 主流程。

    输入：
    - 无

    输出：
    - 无，结果会保存到 outputs 目录
    """
    # 读取配置并确定本次运行模式
    config = load_config("configs/pipeline_config.json")
    run_mode = get_run_mode(config)
    run_id = build_run_id(run_mode)

    # 加载测试用例
    cases = load_cases("data/test_cases")

    if not cases:
        print("未找到可执行的测试用例。")
        return

    # 逐个执行 case，并把结果保存到同一个 run_id 目录下
    for case in cases:
        case_id = case.get("id", "unknown_case")
        result, workflow_state = run_pipeline_with_state(
            case=case,
            config=config,
            run_id=run_id,
        )

        # 在最终结果中显式记录当前运行模式，便于人工对比
        result["run_mode"] = run_mode
        result["workflow_state"] = workflow_state

        output_path = save_result(
            result=result,
            case_id=case_id,
            run_id=run_id,
        )
        print(f"已完成 case={case_id}，结果保存到：{output_path}")


if __name__ == "__main__":
    main()
