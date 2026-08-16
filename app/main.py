"""
项目运行入口。

主要流程：
1. 读取 data 下的需求文本
2. 调用多 Agent 工作流
3. 打印完整结果

设计考虑：
- main.py 只做启动和输出，不承载具体业务逻辑
- 真正的 Agent 串行流程统一放在 workflows/run_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

from workflows.run_pipeline import run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_REQUIREMENT_PATH = PROJECT_ROOT / "data" / "sample_requirements_v1.md"


def load_requirement_text(file_path: Path) -> str:
    """
    读取需求文本文件内容。

    输入：
    - file_path：需求文件路径

    输出：
    - 需求文本字符串
    """
    if not file_path.exists():
        raise FileNotFoundError(f"需求文件不存在：{file_path}")

    file_text = file_path.read_text(encoding="utf-8").strip()

    if not file_text:
        raise ValueError(f"需求文件为空：{file_path}")

    return file_text


def main() -> None:
    """
    启动项目主流程。

    输入：
    - 无

    输出：
    - 无，直接打印结果
    """
    requirement_text = load_requirement_text(SAMPLE_REQUIREMENT_PATH)

    # 运行完整的 4 Agent 串行流程
    pipeline_result = run_pipeline(requirement_text)

    print("===== Pipeline Result =====")
    print(json.dumps(pipeline_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()