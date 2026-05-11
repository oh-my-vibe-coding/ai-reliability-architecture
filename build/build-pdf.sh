#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# 构建 PDF · Pandoc + XeLaTeX
# 从书根目录执行：bash build/build-pdf.sh
# 输出：output/AI时代SRE架构师之路-v${VERSION}.pdf
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# --- 配置 ---
VERSION="${VERSION:-v1.2.0}"
OUTPUT_DIR="output"
OUTPUT_FILE="${OUTPUT_DIR}/AI时代SRE架构师之路-${VERSION}.pdf"
BUILD_DIR="build"
METADATA="${BUILD_DIR}/pdf-metadata.yaml"
STYLE="${BUILD_DIR}/pdf-style.tex"

# --- 颜色输出 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { printf "${GREEN}==>${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}WARN${NC} %s\n" "$*" >&2; }
die()   { printf "${RED}ERR${NC} %s\n" "$*" >&2; exit 1; }

# --- 预检：必须在书根运行 ---
if [[ ! -f "mkdocs.yml" && ! -f "README.md" ]]; then
  die "请在书根目录执行此脚本（当前: $(pwd)）"
fi

# --- 预检：pandoc ---
if ! command -v pandoc >/dev/null 2>&1; then
  cat <<EOF >&2
${RED}错误${NC}：未检测到 pandoc。

安装方式：
  macOS:   brew install pandoc
  Ubuntu:  sudo apt-get install pandoc
  Windows: choco install pandoc 或从 https://pandoc.org/installing.html 下载

EOF
  exit 1
fi

PANDOC_VERSION=$(pandoc --version | head -1)
info "pandoc: ${PANDOC_VERSION}"

# --- 预检：xelatex ---
if ! command -v xelatex >/dev/null 2>&1; then
  cat <<EOF >&2
${RED}错误${NC}：未检测到 xelatex（LaTeX 引擎）。

安装方式（注意：TeX 发行版较大，3-4 GB）：
  macOS:   brew install --cask mactex-no-gui
           （如果磁盘紧张也可用 basictex 再按需加包：
            brew install --cask basictex
            sudo tlmgr install xecjk ctex fontspec titlesec booktabs mdframed framed enumitem
           ）
  Ubuntu:  sudo apt-get install texlive-xetex texlive-fonts-recommended texlive-lang-chinese texlive-latex-extra
  Windows: 安装 MiKTeX 或 TeX Live: https://miktex.org/

若暂时不想装 LaTeX，可改用 build/build-site.sh 生成 HTML 站点 + 浏览器"打印为 PDF"。
EOF
  exit 1
fi

XELATEX_VERSION=$(xelatex --version | head -1)
info "xelatex: ${XELATEX_VERSION}"

# --- 预检：中文字体 ---
if command -v fc-list >/dev/null 2>&1; then
  if fc-list :lang=zh | grep -qiE "noto serif cjk|source han serif|songti|pingfang|stsong"; then
    info "中文字体：已检测到至少一种可用"
  else
    warn "未检测到 Noto CJK / Source Han / 系统中文字体。PDF 可能显示为方块。"
    warn "macOS 装字体: brew install --cask font-noto-serif-cjk-sc font-noto-sans-cjk-sc"
    warn "Ubuntu: sudo apt install fonts-noto-cjk"
  fi
else
  warn "未检测到 fc-list，跳过字体检查（Linux 上需 fontconfig）"
fi

# --- 准备输出目录 ---
mkdir -p "${OUTPUT_DIR}"

# --- 主书版章节（有意裁剪）---
# 原则：读者会从头到尾读的内容；专题 / 参考卷 / 代码 / 维护 工具 不塞进主 PDF
FILES=(
  "README.md"
  "00-前言.md"
  "01-引章-大模型速览.md"

  # 第一部分 · 理念
  "理念/01-AI时代工程师的真实处境.md"
  "理念/02-SRE架构师的角色迁移.md"
  "理念/03-学习能力才是新的护城河.md"

  # 第二部分 · 知识
  "知识/04-系统架构与复合AI可靠性数学.md"
  "知识/05-AI推理服务的可靠性工程.md"
  "知识/06-AI自治与上下文架构约束.md"
  "知识/07-质量可观测性与DataFlywheel.md"
  "知识/08-组织与判断力.md"
  "知识/09-工程底座.md"

  # 第三部分 · 练习（主路径）
  "练习/10-三个核心训练动作.md"
  "练习/周循环总览.md"
  "练习/贯穿项目-SRE事故助手.md"

  # Unit 总览（Week 详情不塞主 PDF，专题卷单出）
  "练习/Unit0-AI大模型上手/总览.md"
  "练习/Unit1-Agent自治与致命三角/总览.md"
  "练习/Unit2-TraceEval统一可观测性/总览.md"
  "练习/Unit3-推理SLO与静默降级/总览.md"
  "练习/Unit4-复合AI可靠性数学/总览.md"
  "练习/Unit5-数值与编译器级调试/总览.md"

  "练习/Capstone-AI生产架构评审包.md"

  # 附录（仅工具类，其他链接到在线站即可）
  "附录/A-每月自检表.md"
  "附录/E-模板库.md"
)

# --- 检查所有文件存在 ---
missing=0
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    warn "缺失：$f"
    missing=$((missing + 1))
  fi
done

if [[ ${missing} -gt 0 ]]; then
  die "有 ${missing} 个文件缺失，中止。"
fi

info "章节数：${#FILES[@]}"
info "输出：${OUTPUT_FILE}"

# --- Pandoc 参数 ---
# 说明：
#   --pdf-engine=xelatex        XeLaTeX 对 CJK 友好
#   --toc --toc-depth=3         自动目录
#   --number-sections           章节编号
#   --top-level-division=chapter 把最高级的 H1 当 chapter
#   --metadata-file=...         PDF 元数据
#   --include-in-header=...     注入 LaTeX preamble
#   --resource-path             允许 Pandoc 解析相对图片路径
#   --fail-if-warnings          警告即失败（出版前严格）：按需开

PANDOC_ARGS=(
  --from markdown+hard_line_breaks+emoji+smart+yaml_metadata_block
  --to pdf
  --pdf-engine=xelatex
  --pdf-engine-opt=-shell-escape
  --metadata-file="${METADATA}"
  --include-in-header="${STYLE}"
  --toc
  --toc-depth=3
  --number-sections
  --top-level-division=chapter
  --resource-path=".:build"
  --wrap=preserve
  --output="${OUTPUT_FILE}"
)

info "开始构建 PDF ..."
echo "----------------------------------------"

# 跑！
if pandoc "${PANDOC_ARGS[@]}" "${FILES[@]}"; then
  echo "----------------------------------------"
  if [[ -f "${OUTPUT_FILE}" ]]; then
    SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    info "✓ PDF 构建成功：${OUTPUT_FILE}  (${SIZE})"
    exit 0
  else
    die "pandoc 声称成功但输出文件不存在：${OUTPUT_FILE}"
  fi
else
  RC=$?
  echo "----------------------------------------" >&2
  cat <<EOF >&2
${RED}PDF 构建失败${NC} (exit ${RC})

常见原因排查：
  1) 字体缺失：检查上方日志里的 "Font ... not found"
     → 安装 Noto CJK 或改 build/pdf-style.tex 的 \setCJKmainfont
  2) LaTeX 包缺失：查找 "! LaTeX Error: File 'xxx.sty' not found"
     → basictex 用户: sudo tlmgr install <package>
  3) Emoji / 特殊字符：检查 "Missing character"
     → 源 MD 里减少 emoji，或注释掉 pdf-style.tex 里的 emoji fallback
  4) 表格 / 代码块溢出：查找 "Overfull \\hbox"
     → 属于警告，不致命；可忽略
  5) 中文断行异常：确认 \XeTeXlinebreaklocale 在 preamble 里生效

想定位具体问题：
  pandoc ${FILES[0]} --pdf-engine=xelatex --include-in-header=${STYLE} -o /tmp/test.pdf
  （一次只编一章，更容易找出是哪章出问题）

EOF
  exit ${RC}
fi
