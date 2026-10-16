#!/usr/bin/env python3
"""Prepare a single book input, rendering Mermaid and preserving source files."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote


def prepare(files, output, renderer, puppeteer_config=None):
    root = Path.cwd().resolve()
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    diagrams = {}
    chapters = []
    replacements = str.maketrans({
        "✅": "[通过]", "❌": "[不通过]", "⬜": "[待完成]", "⏳": "[等待]",
        "①": "(1)", "②": "(2)", "③": "(3)", "④": "(4)",
        "⑤": "(5)", "⑥": "(6)", "⑦": "(7)", "\ufe0f": "",
        "⑧": "(8)", "⑨": "(9)", "⑩": "(10)",
        "⁴": "^4", "⁵": "^5",
    })

    for filename in files:
        source = Path(filename).resolve()
        text = source.read_text(encoding="utf-8")
        text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)

        def diagram(match):
            code = match.group(1)
            key = hashlib.sha256(code.encode()).hexdigest()[:16]
            png = output.parent / f"diagram-{key}.png"
            diagrams[key] = (code, png)
            return f"\n![架构图]({png.as_posix()})\n"

        text = re.sub(r"(?ms)^```mermaid\s*\n(.*?)^```\s*$", diagram, text)
        text = text.translate(replacements)
        text = re.sub(r"[\U0001f300-\U0001faff]", "", text)

        def link(match):
            target, fragment = match.group(1), match.group(2) or ""
            relative = ((source.parent / target).resolve() if target else source).relative_to(root)
            path = relative.as_posix()
            if path == "README.md":
                path = ""
            elif path.endswith("/README.md"):
                path = path[:-9]
            else:
                path = path[:-3] + "/"
            return f"](https://oh-my-vibe-coding.github.io/ai-reliability-architecture/{quote(path)}{fragment})"

        # Convert document links to the online counterpart; fenced code is left intact.
        blocks = re.split(r"(?ms)(^```.*?^```[^\n]*)", text)
        for i in range(0, len(blocks), 2):
            blocks[i] = re.sub(r"]\(((?!https?://)[^\s()#]+\.md)?(#[^\s()]+)?\)", link, blocks[i])
        chapters.append("".join(blocks))

    def render(item):
        key, (code, png) = item
        mmd = output.parent / f"diagram-{key}.mmd"
        mmd.write_text(code, encoding="utf-8")
        cmd = [renderer, "-i", str(mmd), "-o", str(png), "-b", "white", "--size", "1400", "-s", "2"]
        if puppeteer_config:
            cmd += ["-p", puppeteer_config]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"Mermaid rendering failed for {mmd}:\n{result.stderr}")

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(render, diagrams.items()))
    output.write_text("\n\n".join(chapters), encoding="utf-8")
    print(f"Prepared {len(files)} chapters, rendered {len(diagrams)} Mermaid diagrams: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--renderer", default=os.environ.get("MMDC", "mmdc"))
    parser.add_argument("--puppeteer-config", default=os.environ.get("PUPPETEER_CONFIG"))
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    prepare(args.files, args.output, args.renderer, args.puppeteer_config)
