#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# 构建 MkDocs 静态站点
# 从书根目录执行：bash build/build-site.sh
# 输出：site/
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { printf "${GREEN}==>${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}WARN${NC} %s\n" "$*" >&2; }
die()   { printf "${RED}ERR${NC} %s\n" "$*" >&2; exit 1; }

# 预检：书根
if [[ ! -f "mkdocs.yml" ]]; then
  die "请在书根目录执行（找不到 mkdocs.yml）。当前: $(pwd)"
fi

# 预检：mkdocs
if ! command -v mkdocs >/dev/null 2>&1; then
  cat <<EOF >&2
${RED}错误${NC}：未检测到 mkdocs。

安装方式（推荐用 venv）：
  python -m venv .venv
  source .venv/bin/activate
  pip install mkdocs mkdocs-material pymdown-extensions

再运行：
  bash build/build-site.sh

EOF
  exit 1
fi

info "mkdocs: $(mkdocs --version)"

# 检查 material 主题
if ! python -c "import material" 2>/dev/null; then
  warn "未检测到 mkdocs-material。运行："
  warn "  pip install mkdocs-material pymdown-extensions"
fi

# --- 建 symlinks（幂等）---
info "建立 docs/ symlink 树 ..."
bash build/setup-symlinks.sh

# 清理旧产物
if [[ -d "site" ]]; then
  info "清理旧的 site/ ..."
  rm -rf site
fi

# 构建
info "开始构建静态站点 ..."
echo "----------------------------------------"

if mkdocs build --strict; then
  echo "----------------------------------------"
  SIZE=$(du -sh site | cut -f1)
  info "✓ 站点构建成功：site/  (${SIZE})"
  echo ""
  echo "本地预览："
  echo "  mkdocs serve"
  echo "  # 或（跑完 build 后）："
  echo "  python -m http.server -d site 8080"
  echo ""
  echo "部署："
  echo "  将 site/ 推到 GitHub Pages / Cloudflare Pages / nginx"
  exit 0
else
  RC=$?
  echo "----------------------------------------" >&2
  warn "严格模式（--strict）下构建失败 (exit ${RC})"
  warn "常见原因："
  warn "  - nav 里的文件路径有误"
  warn "  - Markdown 里有死链"
  warn "  - 扩展配置冲突"
  warn ""
  warn "降级尝试（不用 --strict）："
  warn "  mkdocs build"
  exit ${RC}
fi
