"""
统一封装大模型调用。

主要流程：
1. 读取项目配置
2. 初始化 OpenAI 兼容客户端
3. 发送 prompt
4. 返回模型文本结果

设计考虑：
- 当前只做最小文本调用，不加重试、不加流式输出
- 后面如果你要切换 OpenAI / DeepSeek / 其他兼容接口，只改这里
"""

from __future__ import annotations

from openai import OpenAI

from config.settings import load_settings


def call_llm(prompt_text: str) -> str:
    """
    调用大模型并返回文本结果。

    输入：
    - prompt_text：完整提示词文本

    输出：
    - 模型返回的字符串结果
    """
    settings = load_settings()

    # 统一在这里初始化客户端，其他模块不直接接触底层调用细节
    client = OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
    )

    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {
                "role": "user",
                "content": prompt_text,
            }
        ],
        temperature=0.2,
    )

    result_text = response.choices[0].message.content

    if result_text is None or not result_text.strip():
        raise RuntimeError("模型返回内容为空。")

    return result_text.strip()