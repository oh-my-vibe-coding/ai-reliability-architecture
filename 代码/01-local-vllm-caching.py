"""
01-local-vllm-caching.py
---
本地 vLLM 的 Prompt Caching 示范（对照 Anthropic / OpenAI 云端版）。

⚠️  快照提示
--------------------------------------------------
本文件包含 vLLM 启动参数、API 字段、默认行为等快变信息。
内容快照日期为 2026-05-05；vLLM 迭代快（0.x 系列仍在变），
实际部署前请查官方 docs：
    https://docs.vllm.ai/
--------------------------------------------------

关键特点：
- vLLM 0.20+ 默认开启 Automatic Prefix Caching（APC）
- 完全本地，无 API 成本，但需要 GPU + 自己部署
- 缓存按 block 级（16 token 一 block），可共享到所有请求
- 无 TTL 概念，按 LRU 驱逐

关联章节：深入 02；深入 03 · §4.5（vLLM features）
启动 vLLM server：
    python -m vllm.entrypoints.openai.api_server \
        --model meta-llama/Llama-3-8B-Instruct \
        --enable-prefix-caching \
        --port 8000
"""

from openai import OpenAI

# vLLM 兼容 OpenAI API，改 base_url 即可
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",  # vLLM 默认不校验
)

SYSTEM_PROMPT = """你是一个 SRE 助手。按以下原则回答：
- 优先给可验证的结论
- 涉及生产操作必须强调可回滚性
- 不确定时明说"我不确定"
...（假设这里是 3000 token 的详细系统提示）
"""

LARGE_CONTEXT = "假设这是一份 10000 token 的 runbook"


def ask_with_caching(question: str):
    """
    vLLM 的 prefix caching 对用户透明。
    相同 prefix（按 block 16 token 对齐）会自动命中。
    """
    response = client.chat.completions.create(
        model="meta-llama/Llama-3-8B-Instruct",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{LARGE_CONTEXT}\n\n问题：{question}"},
        ],
    )

    # vLLM 通过 /metrics endpoint 暴露 cache hit rate（Prometheus）
    # 单次调用的 usage 里不会直接给缓存信息
    usage = response.usage
    print(f"Total prompt tokens: {usage.prompt_tokens}")
    print(f"Output tokens: {usage.completion_tokens}")
    print("Cache hit rate: 见 /metrics（vllm:cache_hit_rate）")

    return response.choices[0].message.content


# ---- vLLM 独特特性 ----
# 1. 缓存跨所有请求共享（同 model 同 tokenizer）
# 2. 没有 API key 的隔离（自建服务）
# 3. APC 默认开（vLLM 0.20+），SGLang RadixAttention 类似
# 4. 监控通过 /metrics：
#    - vllm:prefix_cache_hits_total
#    - vllm:prefix_cache_queries_total
#    - 计算 hit rate = hits / queries

# ---- 自建 vs 云端的 trade-off ----
# 自建（vLLM / SGLang）：
#   + 缓存跨用户共享（多租户 RAG 可以共享文档 cache）
#   + 可控 TTL / 驱逐策略
#   + 无 API 限流
#   - 要自己运维（容量 / 监控 / 升级）
#   - GPU 成本固定（vs 云 API 按量）
#
# 云端（Anthropic / OpenAI / Gemini）：
#   + 免运维
#   + 按量付费
#   - 缓存不跨客户
#   - 路由亲和不保证

if __name__ == "__main__":
    print("=== 运行本例前，启动 vLLM server ===")
    print("python -m vllm.entrypoints.openai.api_server \\")
    print("  --model meta-llama/Llama-3-8B-Instruct \\")
    print("  --enable-prefix-caching")
    print()
    print("然后再运行此脚本。")
    print()

    print("=== 第一次调用 ===")
    ask_with_caching("系统 CPU 使用率 90% 该怎么排查？")

    print("\n=== 第二次调用（prefix 命中）===")
    ask_with_caching("用户报告登录慢，排查步骤？")

    # 查命中率：curl http://localhost:8000/metrics | grep prefix_cache
