"""
运行结果保存器。

作用：
- 按传入的 run_id 创建输出目录
- 按 case_id 保存单条输出结果
- 返回实际保存路径

主要流程：
1. 接收 main.py 生成好的 run_id
2. 创建对应输出目录
3. 将当前 case 结果写入 json 文件

设计考虑：
- run_id 必须在一次运行开始时只生成一次
- 同一次运行的所有 case 必须落在同一个目录下
- 当前不做自动评估和复杂 diff，只保留最小人工对比能力
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def save_result(
    result: Dict[str, Any],
    case_id: str,
    run_id: str,
    output_root: str | Path = "outputs",
) -> str:
    """
    保存单条 case 的执行结果。

    输入：
    - result: pipeline 输出结果
    - case_id: 测试用例 ID
    - run_id: 本次运行唯一标识
    - output_root: 输出根目录

    输出：
    - 实际保存文件路径
    """
    # 根据 run_id 创建本次运行的输出目录
    output_dir = Path(output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 按 case_id 保存单独结果文件
    output_path = output_dir / f"{case_id}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    return str(output_path)