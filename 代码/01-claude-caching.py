"""
01-claude-caching.py
---
带 Prompt Caching 的最小 Claude 客户端。

演示：
- cache_control 的 ephemeral 标记
- 如何观测 cache_creation vs cache_read token
- 多段缓存点的设置

对应章节：深入 02 · Prompt Caching 原理
"""

import os
from anthropic import Anthropic

client = Anthropic()  # 从 ANTHROPIC_API_KEY 环境变量读

# ---- 1. 简单带 caching 的调用 ----

SYSTEM_PROMPT = """你是一个 SRE 助手。按以下原则回答：
- 优先给可验证的结论
- 涉及生产操作必须强调可回滚性
- 不确定时明说"我不确定"
...（假设这里是 3000 token 的详细系统提示）
"""

LARGE_CONTEXT = open("/path/to/your/runbook.md").read() if False else "假设这是一份 10000 token 的 runbook"


def ask_with_caching(question: str):
    """
    关键点：system 里标 cache_control，后续相同 system 请求会命中缓存。
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",  # 或其他版本
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # ← 这里标记
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": LARGE_CONTEXT,
                        "cache_control": {"type": "ephemeral"},  # 第二个缓存点
                    },
                    {
                        "type": "text",
                        "text": question,  # 变化部分，不缓存
                    },
                ],
            }
        ],
    )

    # 打印 token 使用情况
    usage = response.usage
    print(f"Input tokens (未缓存): {usage.input_tokens}")
    print(f"Cache creation tokens (写入): {usage.cache_creation_input_tokens}")
    print(f"Cache read tokens (命中): {usage.cache_read_input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")

    total_input = (
        usage.input_tokens
        + usage.cache_creation_input_tokens
        + usage.cache_read_input_tokens
    )
    if total_input > 0:
        hit_rate = usage.cache_read_input_tokens / total_input
        print(f"Cache hit rate: {hit_rate:.1%}")

    return response.content[0].text


# ---- 2. 演示缓存的效果 ----

if __name__ == "__main__":
    print("=== 第一次调用（写入缓存）===")
    ask_with_caching("系统 CPU 使用率 90% 该怎么排查？")

    print("\n=== 第二次调用（应该命中缓存）===")
    ask_with_caching("用户报告登录慢，排查步骤？")

    # 预期输出：
    # 第一次：cache_creation 高，cache_read=0
    # 第二次：cache_creation=0，cache_read 高，成本降 ~10x

    # ---- SRE 监控建议 ----
    # 生产上把这些指标打到 Prometheus：
    # - cache_hit_rate  （目标 > 80%）
    # - cache_creation_token_rate（突增 = prefix 变了）
    # - cache_read_token_rate
    # - total_cost_per_request
