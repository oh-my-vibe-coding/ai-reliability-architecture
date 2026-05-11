"""
02-minimal-agent.py
---
Tool use + 流式输出的最小 Agent。

演示：
- 如何声明工具
- Agent 循环（请求 → 模型决定调工具 → 执行 → 回灌 → 继续）
- 流式输出显示
- 最小安全边界（白名单命令）

对应章节：Unit 0 · Week 1 · API 与工具调用；深入 07 · 致命三角
"""

import subprocess
import json
from anthropic import Anthropic

client = Anthropic()

# ---- 1. 工具定义 ----

TOOLS = [
    {
        "name": "run_shell",
        "description": (
            "在本机运行一个白名单内的 shell 命令。"
            "只支持只读命令：uptime, df -h, ls, ps, free。"
            "禁止 rm、mv、sudo、pipe、重定向。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令（必须在白名单内）",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "读取本地文件内容。仅限 /tmp 和 /var/log 下的文件。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件绝对路径"},
            },
            "required": ["path"],
        },
    },
]

# ---- 2. 工具执行（含安全检查）----

SAFE_COMMANDS = {"uptime", "df", "ls", "ps", "free"}


def run_shell(command: str) -> str:
    """白名单执行"""
    base = command.strip().split()[0] if command.strip() else ""
    if base not in SAFE_COMMANDS:
        return f"ERROR: command '{base}' not in whitelist"
    if any(c in command for c in [";", "|", ">", "<", "&&", "`"]):
        return "ERROR: pipes/redirects not allowed"
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout[:2000] + (result.stderr[:500] if result.stderr else "")
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out"
    except Exception as e:
        return f"ERROR: {e}"


def read_file(path: str) -> str:
    """路径白名单 + 长度限制"""
    if not (path.startswith("/tmp/") or path.startswith("/var/log/")):
        return f"ERROR: path {path} not in allowed directories"
    try:
        with open(path, "r") as f:
            content = f.read(10000)  # 最多 10k 字符
        return content
    except Exception as e:
        return f"ERROR: {e}"


TOOL_IMPL = {
    "run_shell": lambda input: run_shell(input["command"]),
    "read_file": lambda input: read_file(input["path"]),
}


# ---- 3. Agent 循环（带流式）----

def run_agent(user_message: str, max_iterations: int = 10):
    messages = [{"role": "user", "content": user_message}]

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        # 调用 API（这里用非流式简化；生产上推荐流式）
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            tools=TOOLS,
            messages=messages,
        )

        # 把助手响应加到对话
        messages.append({"role": "assistant", "content": response.content})

        # 看 stop reason
        if response.stop_reason == "end_turn":
            # 输出文本，结束
            for block in response.content:
                if block.type == "text":
                    print(block.text)
            break

        if response.stop_reason == "tool_use":
            # 执行所有 tool_use
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[Tool call] {block.name}({json.dumps(block.input)})")
                    result = TOOL_IMPL[block.name](block.input)
                    print(f"[Tool result] {result[:200]}...")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            # 回灌结果
            messages.append({"role": "user", "content": tool_results})
        else:
            # max_tokens 或其他原因
            print(f"Stopped: {response.stop_reason}")
            break
    else:
        print("Max iterations reached, stopping")


# ---- 4. 运行示例 ----

if __name__ == "__main__":
    print("=== 例 1：让 Agent 查磁盘 ===")
    run_agent("帮我看下这台机器的磁盘是不是快满了")

    print("\n\n=== 例 2：让 Agent 综合检查 ===")
    run_agent("这台机器健康吗？请查 uptime、内存、磁盘")

    # ---- 学习要点 ----
    # 1. 模型决定调用工具（不是你）
    # 2. 你的代码执行工具、回灌结果
    # 3. 模型基于结果决定下一步（继续调工具 or 给答案）
    # 4. Tool 返回被当 context 的一部分 — 需防 indirect injection
    # 5. 循环要有上限（max_iterations），避免 Pattern 4 tool abuse loop
