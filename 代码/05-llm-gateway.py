"""
05-llm-gateway.py
---
最小 LLM 网关：包装 Anthropic API，加 token 计账、cache 监控、per-tenant 限流。
FastAPI 实现。

演示：
- LLM 代理的核心功能：计账 + 监控 + 限流
- Cache hit rate 的追踪
- Per-tenant 的成本账

对应章节：深入 04 · token 账本；深入 10 · Pattern 2/4/7/9
"""

import time
from collections import defaultdict
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

app = FastAPI()
claude = Anthropic()

# ---- 1. 计账数据结构（生产用 Redis / DB）----


class TenantUsage:
    def __init__(self):
        self.input_tokens = 0
        self.cache_creation_tokens = 0
        self.cache_read_tokens = 0
        self.output_tokens = 0
        self.requests = 0
        self.last_reset = time.time()


tenant_usage: dict[str, TenantUsage] = defaultdict(TenantUsage)

# ---- 2. 限流配置 ----

RATE_LIMIT_TPM = 100_000  # 每分钟 input token 上限（每 tenant）
BUDGET_PER_DAY_USD = 50  # 每 tenant 每天预算（粗算）

# 粗估定价（Sonnet 4.6）：$3/Mtok in, $15/Mtok out
PRICE_IN = 3 / 1_000_000
PRICE_CACHE_CREATE = 3.75 / 1_000_000
PRICE_CACHE_READ = 0.3 / 1_000_000
PRICE_OUT = 15 / 1_000_000


def estimate_cost(u: TenantUsage) -> float:
    return (
        u.input_tokens * PRICE_IN
        + u.cache_creation_tokens * PRICE_CACHE_CREATE
        + u.cache_read_tokens * PRICE_CACHE_READ
        + u.output_tokens * PRICE_OUT
    )


# ---- 3. 请求模型 ----


class ChatRequest(BaseModel):
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    system: list[dict] | str | None = None
    messages: list[dict]


# ---- 4. 核心端点 ----


@app.post("/v1/chat")
async def chat(req: ChatRequest, x_tenant: str = Header(...)):
    # ---- 限流 ----
    u = tenant_usage[x_tenant]

    # 每分钟窗口（简化实现）
    now = time.time()
    if now - u.last_reset > 60:
        # 这里应该用滑动窗口 / leaky bucket，我们偷懒用简单重置
        u.input_tokens = u.cache_creation_tokens = u.cache_read_tokens = 0
        u.last_reset = now

    if u.input_tokens > RATE_LIMIT_TPM:
        raise HTTPException(429, "rate limited")

    # ---- 预算检查 ----
    if estimate_cost(u) > BUDGET_PER_DAY_USD:
        raise HTTPException(402, "daily budget exceeded")

    # ---- 调用 ----
    try:
        kwargs = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": req.messages,
        }
        if req.system:
            kwargs["system"] = req.system

        response = claude.messages.create(**kwargs)
    except Exception as e:
        raise HTTPException(502, f"upstream error: {e}")

    # ---- 记账 ----
    usage = response.usage
    u.input_tokens += usage.input_tokens
    u.cache_creation_tokens += usage.cache_creation_input_tokens
    u.cache_read_tokens += usage.cache_read_input_tokens
    u.output_tokens += usage.output_tokens
    u.requests += 1

    # ---- 返回 ----
    text = "".join(b.text for b in response.content if b.type == "text")

    return {
        "content": text,
        "usage": {
            "input_tokens": usage.input_tokens,
            "cache_creation_tokens": usage.cache_creation_input_tokens,
            "cache_read_tokens": usage.cache_read_input_tokens,
            "output_tokens": usage.output_tokens,
        },
        "tenant_stats": {
            "cumulative_cost_usd": round(estimate_cost(u), 4),
            "cache_hit_rate": (
                round(
                    u.cache_read_tokens
                    / max(1, u.cache_read_tokens + u.cache_creation_tokens + u.input_tokens),
                    3,
                )
            ),
            "requests_served": u.requests,
        },
    }


# ---- 5. 监控端点（给 Prometheus scrape）----


@app.get("/metrics")
def metrics():
    """Prometheus 格式简化版"""
    lines = []
    for tenant, u in tenant_usage.items():
        lines.append(f'llm_input_tokens_total{{tenant="{tenant}"}} {u.input_tokens}')
        lines.append(
            f'llm_cache_read_tokens_total{{tenant="{tenant}"}} {u.cache_read_tokens}'
        )
        lines.append(
            f'llm_cache_creation_tokens_total{{tenant="{tenant}"}} {u.cache_creation_tokens}'
        )
        lines.append(f'llm_output_tokens_total{{tenant="{tenant}"}} {u.output_tokens}')
        lines.append(f'llm_requests_total{{tenant="{tenant}"}} {u.requests}')
        lines.append(
            f'llm_cost_usd_total{{tenant="{tenant}"}} {estimate_cost(u):.4f}'
        )
        total_in = u.cache_read_tokens + u.cache_creation_tokens + u.input_tokens
        hit_rate = u.cache_read_tokens / total_in if total_in else 0
        lines.append(f'llm_cache_hit_rate{{tenant="{tenant}"}} {hit_rate:.3f}')
    return "\n".join(lines)


# ---- 6. 运行 ----
# uvicorn 05-llm-gateway:app --port 8000
#
# 调用示例：
# curl -X POST http://localhost:8000/v1/chat \
#   -H "X-Tenant: team-a" \
#   -H "Content-Type: application/json" \
#   -d '{"messages": [{"role": "user", "content": "你好"}]}'
#
# 监控：
# curl http://localhost:8000/metrics
#
# ---- 下一步改造 ----
# 1. 把 tenant_usage 存 Redis（否则重启清零）
# 2. 细粒度限流（滑动窗口 / token bucket）
# 3. 路由：根据 model 选不同 provider
# 4. Fallback：主 provider 挂了切备用
# 5. Prompt injection 检测前置
# 6. Audit log（所有 prompt 留档，脱敏）
# 7. Tracing：OpenTelemetry
