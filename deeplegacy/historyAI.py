"""
兼容脚本：用于 crontab/手动运行，生成“早安历史”文案。

注意：
1) 已移除硬编码 API Key（安全原因）
2) 统一走 LiteLLM（支持 Gemini/OpenAI/Anthropic/DeepSeek...），通过 .env 配置模型与 Key

运行示例：
  uv run python deeplegacy/historyAI.py
"""

from __future__ import annotations

import asyncio

from deeplegacy.agent import agent


async def main() -> None:
    result = await agent.run()
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
