"""
MkDocs hook: convert GitHub-style callouts to MkDocs Material admonitions.

源 Markdown 里用的是 GitHub Alerts 语法（跨 GitHub / Obsidian / Typora 兼容）：

    > [!NOTE]
    > 正文第一行
    > 正文第二行

MkDocs Material 原生不解析 GitHub Alerts（依赖 pymdownx.blocks 或扩展）。
本 hook 在页面渲染前把它转成 MkDocs admonition 语法：

    !!! note

        正文第一行
        正文第二行

这样源文件保持 vendor-neutral，站点照样渲染出漂亮的 callout。

映射表（GitHub → Material）:
  NOTE      → note    (blue)
  TIP       → tip     (green)
  IMPORTANT → info    (teal-ish)
  WARNING   → warning (amber)
  CAUTION   → danger  (red)

进阶：如果 callout 首行（在 `[!TYPE]` 之后）有标题文本，也可以支持
    > [!NOTE] 自定义标题
但当前 hook 保守实现 —— 不强制要求标题。
"""

from __future__ import annotations
import re

_CALLOUT_RE = re.compile(
    r"""
    ^(?P<indent>[ \t]*)         # 前导空白（允许缩进在 list 内）
    >[ \t]*\[!(?P<kind>NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]
    [ \t]*(?P<title>[^\n]*)\n   # 可选标题（通常为空）
    (?P<body>(?:^[ \t]*>.*\n?)*) # 后续 `> ...` 行
    """,
    re.MULTILINE | re.VERBOSE,
)

_TYPE_MAP = {
    "NOTE": "note",
    "TIP": "tip",
    "IMPORTANT": "info",
    "WARNING": "warning",
    "CAUTION": "danger",
}


def _convert(match: re.Match) -> str:
    indent = match.group("indent")
    kind = _TYPE_MAP[match.group("kind")]
    title = match.group("title").strip()
    body = match.group("body")

    # 把每一行 `> something` 的 `> ` 前缀去掉
    body_lines = []
    for line in body.splitlines():
        stripped = re.sub(r"^[ \t]*>[ \t]?", "", line)
        body_lines.append(stripped)

    # 去掉首尾空行
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    # MkDocs admonition 要求正文缩进 4 个空格
    inner = "\n".join(f"{indent}    {line}" if line.strip() else "" for line in body_lines)

    header = f'{indent}!!! {kind}'
    if title:
        header += f' "{title}"'

    return f"{header}\n\n{inner}\n"


def on_page_markdown(markdown: str, **kwargs) -> str:
    """MkDocs hook entry point. See: https://www.mkdocs.org/user-guide/configuration/#hooks"""
    return _CALLOUT_RE.sub(_convert, markdown)
