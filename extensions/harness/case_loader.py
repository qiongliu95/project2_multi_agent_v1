"""
测试用例加载器。

作用：
- 从指定目录读取所有 case 文件
- 返回标准化 case 列表

主要流程：
1. 扫描目录下的 json 文件
2. 读取内容
3. 校验基础字段
4. 返回 case 列表

设计考虑：
- 当前只支持 json
- 最低要求 case 必须包含 id 和 requirement_text
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_cases(cases_dir: str | Path) -> List[Dict[str, Any]]:
    """
    加载指定目录下的全部测试用例。

    输入：
    - cases_dir: 测试用例目录

    输出：
    - case 列表
    """
    directory = Path(cases_dir)
    if not directory.exists():
        return []

    loaded_cases: List[Dict[str, Any]] = []

    # 遍历目录，读取所有 json 用例
    for case_path in sorted(directory.glob("*.json")):
        with case_path.open("r", encoding="utf-8") as file:
            case_data = json.load(file)

        # 过滤掉结构不完整的 case，避免 runner 崩掉
        if "id" not in case_data or "requirement_text" not in case_data:
            continue

        loaded_cases.append(case_data)

    return loaded_cases