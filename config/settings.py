"""
加载项目运行配置。

主要流程：
1. 从 .env 读取环境变量
2. 校验 API Key / Base URL / Model 是否存在
3. 返回统一的配置对象

设计考虑：
- 当前项目只保留最小 MVP 所需配置
- 如果环境变量缺失，直接报错，避免后面调用时才发现问题
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    """
    保存项目运行配置。

    输入：
    - 无，字段值来自环境变量

    输出：
    - 一个配置对象，供其他模块读取
    """

    api_key: str
    base_url: str
    model_name: str


def load_settings() -> Settings:
    """
    读取并校验环境变量配置。

    输入：
    - 无

    输出：
    - Settings 配置对象
    """
    load_dotenv()

    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    model_name = os.getenv("LLM_MODEL", "").strip()

    # 这里先做前置校验，避免后面调用模型时才暴露错误
    if not api_key:
        raise ValueError("缺少环境变量：LLM_API_KEY")
    if not base_url:
        raise ValueError("缺少环境变量：LLM_BASE_URL")
    if not model_name:
        raise ValueError("缺少环境变量：LLM_MODEL")

    return Settings(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
    )