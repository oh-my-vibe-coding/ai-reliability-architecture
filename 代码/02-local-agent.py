"""
02-local-agent.py
---
本地 LLM（Ollama / vLLM）的最小 Agent（对照云端版）。

⚠️  快照提示
--------------------------------------------------
本文件包含**本地模型名、tool use 支持度、Ollama / vLLM API 接口**
等快变信息。内容快照日期为 2026-05-05；开源模型和本地推理栈
迭代极快，实际部署前请查官方 docs：
    https://ollama.com/library
    https://docs.vllm.ai/
    Qwen / Llama / Mistral 各自 HuggingFace model card
--------------------------------------------------

关键差异（vs Anthropic / OpenAI）：
- 用本地开源模型（Llama 3 / Qwen 3 / Mistral 等）
- 完全隔离，无 API 成本，数据不出本地
- Tool use 能力**取决于模型**：并非所有开源模型都训了好的 tool use
  - Llama 3.1 Instruct: ⭐⭐⭐ 可用
  - Qwen 3: ⭐⭐⭐⭐ 较好
  - 小模型（7B 以下）tool use 不稳

关联章节：Unit 0；深入 03 · §3.8-3.9

准备：
    # 方案 A: Ollama
    ollama pull qwen3:8b
    ollama serve

    # 方案 B: vLLM
    python -m vllm.entrypoints.openai.api_server \\
        --model Qwen/Qwen3-8B \\
        --enable-auto-tool-choice \\
        --tool-call-parser hermes
"""

import json
import subprocess
from openai import OpenAI

# Ollama 或 vLLM 都兼容 OpenAI API
client = OpenAI(
    base_url="http://localhost:11434/v1",  # Ollama 默认
    # base_url="http://localhost:8000/v1",  # vLLM 默认
    api_key="not-needed",
)

MODEL = "qwen3:7b"  # 或 llama3.1:8b / mistral:7b

# ---- 复用云端版的工具定义和执行 ----

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "在本机运行白名单命令：uptime, df -h, ls, ps, free",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]

SAFE_COMMANDS = {"uptime", "df", "ls", "ps", "free"}


def run_shell(command: str) -> str:
    base = command.strip().split()[0] if command.strip() else ""
    if base not in SAFE_COMMANDS:
        return f"ERROR: command '{base}' not in whitelist"
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=5)
        return result.stdout[:2000]
    except Exception as e:
        return f"ERROR: {e}"


TOOL_IMPL = {"run_shell": lambda args: run_shell(args["command"])}


def run_agent(user_message: str, max_iterations: int = 5):
    messages = [{"role": "user", "content": user_message}]

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0,  # 本地模型对 temperature 更敏感，给低点更稳
        )

        message = response.choices[0].message
        messages.append(message)

        # 本地模型的 finish_reason 可能不标准，防御式处理
        if message.tool_calls:
            for tc in message.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    print(f"[WARN] 本地模型 tool args 不是 valid JSON: {tc.function.arguments}")
                    # 降级：假装 tool 失败，让模型自己处理
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "ERROR: invalid tool arguments",
                    })
                    continue

                print(f"[Tool call] {name}({args})")
                result = TOOL_IMPL.get(name, lambda _: "ERROR: unknown tool")(args)
                print(f"[Tool result] {result[:200]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            # 没 tool_calls，说明 model 给了最终回答
            if message.content:
                print(message.content)
            break
    else:
        print("Max iterations reached")


# ---- 本地模型 Agent 的独特挑战 ----
#
# 1. Tool use 质量远不如 Claude/GPT
#    - 可能忽略工具（"算了我直接答"）
#    - 可能无限循环调同一 tool
#    - JSON 参数有时不 valid
#
# 2. Temperature 调低（0 或 0.1）
#    - 本地模型 temperature 1.0 几乎不可用
#
# 3. 必须限制 max_iterations 更严
#    - 5 而不是 10，因为更容易乱
#
# 4. 要防御式处理 tool_calls
#    - 检查 JSON 合法性
#    - 检查 name 在 TOOL_IMPL 里
#    - 准备好降级路径
#
# 5. 性能：
#    - 本地 7B 模型单次 latency 约 2-5 秒（CPU 慢，GPU 快）
#    - 多轮 tool use 累积到 10-30 秒
#    - 对交互式体验不够快

# ---- 什么场景推荐本地 Agent ----
#
# ✅ 数据敏感不能出本地
# ✅ 不需要 frontier 能力（简单任务）
# ✅ 高吞吐低延迟需求（批处理）
# ✅ 成本极敏感（规模化后 API 账单难承受）
#
# ❌ Agent 能力重度依赖（用 Claude / GPT）
# ❌ Multi-step reasoning 复杂任务
# ❌ 需要广域知识（本地模型训练截止日更早）

if __name__ == "__main__":
    print("=== 准备 ===")
    print("确保 Ollama 正在跑：ollama serve")
    print(f"模型：{MODEL}")
    print()

    run_agent("帮我看下磁盘和内存用量")
