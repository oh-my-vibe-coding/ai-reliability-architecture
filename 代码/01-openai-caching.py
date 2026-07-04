"""
01-openai-caching.py
---
OpenAI 版本的 Prompt Caching 示范（对照 01-claude-caching.py）。

⚠️  快照提示
--------------------------------------------------
本文件包含模型名、定价、厂商能力等快变信息。
内容快照日期为 2026-07-04；实际选型或上线前，请以厂商
官方 pricing 和当前生产验证为准：
    https://openai.com/api/pricing
    https://platform.openai.com/docs/models
--------------------------------------------------

关键差异（vs Anthropic）：
- OpenAI 是**自动 caching**，不需要 cache_control 显式标记
- 最小 token 数 1024（Anthropic 随模型 512–4096 不等）
- 折扣按代际：gpt-4o 代 50%、GPT-4.1 代 75%、GPT-5 系 90%
- 不分写入/读取，没写入额外成本

对应章节：深入 02 · §4（三家对比）
"""

import os
from openai import OpenAI

client = OpenAI()  # OPENAI_API_KEY

SYSTEM_PROMPT = """你是一个 SRE 助手。按以下原则回答：
- 优先给可验证的结论
- 涉及生产操作必须强调可回滚性
- 不确定时明说"我不确定"
...（假设这里是 3000 token 的详细系统提示）
"""

LARGE_CONTEXT = "假设这是一份 10000 token 的 runbook"


def ask_with_caching(question: str):
    """
    OpenAI 的自动 caching：长 prompt 自动命中，无需显式标记。
    """
    response = client.chat.completions.create(
        model="gpt-5-mini",  # 或 gpt-5 / gpt-5-nano
        max_completion_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{LARGE_CONTEXT}\n\n问题：{question}"},
        ],
    )

    # OpenAI 返回的 usage 字段
    usage = response.usage
    print(f"Total input tokens: {usage.prompt_tokens}")
    print(f"Cached input tokens: {usage.prompt_tokens_details.cached_tokens}")
    print(f"Output tokens: {usage.completion_tokens}")

    if usage.prompt_tokens > 0:
        hit_rate = usage.prompt_tokens_details.cached_tokens / usage.prompt_tokens
        print(f"Cache hit rate: {hit_rate:.1%}")

    return response.choices[0].message.content


# ---- 成本对照（近似，2026-07）----
# OpenAI GPT-5 mini:
#   - 常规输入: $0.25/MTok
#   - 缓存输入: $0.025/MTok（折扣 90%——GPT-5 系口径；gpt-4o 代只有 50%）
# Anthropic Sonnet 4.6:
#   - 常规输入: $3/MTok
#   - 缓存写入: $3.75/MTok（+25%）
#   - 缓存读取: $0.30/MTok（折扣 90%）
#
# 规模化场景下（对端为 GPT-5 系时读取折扣打平，都省 90%）：
# - 低重用 / 低频场景: OpenAI 更划算（无写入溢价，可选 24h 延长保留）
# - 对端是 gpt-4o / GPT-4.1 代且高重用: Anthropic 反而更省钱

# ⚠️ 运行前：把 SYSTEM_PROMPT / LARGE_CONTEXT 替换为真实长文本（合计 ≥1024 token）。
# 仓库里是几十 token 的占位文本，低于 OpenAI 最小缓存门槛（1024，自动缓存不生效），
# 直接运行两次调用的 cached_tokens 都会是 0，下面的"部分命中"不会出现。
if __name__ == "__main__":
    print("=== 第一次调用（无缓存）===")
    ask_with_caching("系统 CPU 使用率 90% 该怎么排查？")

    print("\n=== 第二次调用（部分命中）===")
    ask_with_caching("用户报告登录慢，排查步骤？")

    # 观察：OpenAI 不明确区分 cache_creation，但 prompt_tokens_details.cached_tokens
    # 会显示命中了多少。重复调用同系统提示，第二次这个数会上升。
