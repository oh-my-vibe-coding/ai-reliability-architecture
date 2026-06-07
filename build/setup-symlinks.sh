#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# 把书根的内容通过 symlink 影射到 docs/ 子目录
# 原因：MkDocs 要求 docs_dir 不能与 mkdocs.yml 同目录
# 行为：幂等（多次执行结果相同；先清理再重建）
#
# 用法：bash build/setup-symlinks.sh
# 被调用：build-site.sh 在 mkdocs build 之前自动调用
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# cd 到书根（脚本位置的父目录）
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
NC='\033[0m'
info() { printf "${GREEN}==>${NC} %s\n" "$*"; }

# --- 需要影射到 docs/ 的顶层内容 ---
# 原则：所有 Markdown 源 + CSS 资源；排除构建产物和非内容目录
INCLUDES=(
  # 根级 Markdown
  "README.md"
  "学习路线图.md"
  "00-前言.md"
  "01-引章-大模型速览.md"
  "阅读版构建.md"
  "样式指南.md"

  # 内容目录
  "理念"
  "知识"
  "架构"
  "练习"
  "深入"
  "科学"
  "共同语言"
  "复习"
  "代码"
  "附录"
  "维护"

  # CSS 资源（mkdocs 从 docs_dir 找）
  "stylesheets"
)

# --- 不要影射（排除）---
# build/、site/、docs/ 本身、hooks/（在 mkdocs.yml 里以书根相对路径引用）
# .gitignore、mkdocs.yml 等配置

# --- 执行 ---
info "Setup 开始（书根 $(pwd)）"

# 清理旧 docs/（只删 symlinks 和空目录，不删真实文件——保险）
if [[ -d docs ]]; then
  # 只删 docs 里的 symlinks
  find docs -maxdepth 1 -type l -delete 2>/dev/null || true
  # 删空的 docs 目录
  rmdir docs 2>/dev/null || {
    # 如果 docs 里还有非 symlink 的东西，不删（可能有别的构建产物）
    true
  }
fi

mkdir -p docs

# 建 symlinks
for item in "${INCLUDES[@]}"; do
  if [[ ! -e "$item" ]]; then
    echo "  skip（不存在）: $item"
    continue
  fi
  # 符号链接 docs/<name> -> ../<item>
  ln -sfn "../$item" "docs/$item"
done

# 单独把 build/README.md 挂进来（其他 build/ 产物是脚本，不进 docs 树）
mkdir -p docs/build
ln -sfn "../../build/README.md" "docs/build/README.md"

info "symlinks 建成（$(find docs -maxdepth 2 -type l | wc -l | tr -d ' ') 个条目）"
info "docs_dir = $(pwd)/docs"
