"""
02-openai-agent.py
---
OpenAI 版本的最小 Agent（对照 02-minimal-agent.py）。

关键差异（vs Anthropic）：
- OpenAI 用 "function calling"（也叫 tool calling），语义相近但字段略不同
- 2025+ OpenAI 推荐用 Responses API（stateful），本例用 Chat Completions 保持对齐
- stop_reason 叫 finish_reason

关联章节：Unit 0 · Week 1；深入 07
"""

import json
import subprocess
from openai import OpenAI

client = OpenAI()

# ---- 1. 工具定义（OpenAI 格式）----

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "在本机运行一个白名单内的 shell 命令。"
                "只支持只读：uptime, df -h, ls, ps, free。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取本地文件（仅 /tmp 和 /var/log）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
]

# ---- 2. 工具执行（复用 02-minimal-agent 的安全检查）----

SAFE_COMMANDS = {"uptime", "df", "ls", "ps", "free"}


def run_shell(command: str) -> str:
    base = command.strip().split()[0] if command.strip() else ""
    if base not in SAFE_COMMANDS:
        return f"ERROR: command '{base}' not in whitelist"
    if any(c in command for c in [";", "|", ">", "<", "&&", "`"]):
        return "ERROR: pipes/redirects not allowed"
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=5)
        return result.stdout[:2000] + (result.stderr[:500] if result.stderr else "")
    except Exception as e:
        return f"ERROR: {e}"


def read_file(path: str) -> str:
    if not (path.startswith("/tmp/") or path.startswith("/var/log/")):
        return f"ERROR: path {path} not in allowed directories"
    try:
        with open(path, "r") as f:
            return f.read(10000)
    except Exception as e:
        return f"ERROR: {e}"


TOOL_IMPL = {
    "run_shell": lambda args: run_shell(args["command"]),
    "read_file": lambda args: read_file(args["path"]),
}


# ---- 3. Agent 循环 ----


def run_agent(user_message: str, max_iterations: int = 10):
    messages = [{"role": "user", "content": user_message}]

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages,
            tools=TOOLS,
        )

        message = response.choices[0].message
        messages.append(message)

        if response.choices[0].finish_reason == "stop":
            if message.content:
                print(message.content)
            break

        if response.choices[0].finish_reason == "tool_calls" and message.tool_calls:
            for tc in message.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                print(f"[Tool call] {name}({args})")

                result = TOOL_IMPL[name](args)
                print(f"[Tool result] {result[:200]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            print(f"Stopped: {response.choices[0].finish_reason}")
            break
    else:
        print("Max iterations reached")


# ---- Anthropic vs OpenAI 关键字段映射 ----
# Anthropic                       OpenAI (Chat Completions)
# --------                        -----------------------
# stop_reason                     finish_reason
# content: [blocks]               message.content + message.tool_calls
# content.type="tool_use"         tool_calls[i].function.name
# tool_use.id                     tool_calls[i].id
# tool_result.tool_use_id         role="tool" + tool_call_id
# messages=[...]                  messages=[...] (相同)


if __name__ == "__main__":
    print("=== 例 1：让 Agent 查磁盘 ===")
    run_agent("帮我看下这台机器的磁盘是不是快满了")

    # ---- 对 Anthropic 用户的迁移建议 ----
    # 1. 工具定义格式不同但逻辑一致
    # 2. 工具执行和回灌的**循环结构**完全相同
    # 3. 多数业务代码可以在一层 adapter 上 swap
    # 4. OpenAI Responses API 是 stateful（服务端存 conversation），
    #    可以消除很多 message list 管理，但要权衡 vendor lock-in
