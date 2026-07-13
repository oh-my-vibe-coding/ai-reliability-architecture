---
title: PDF 构建系统
updated: 2026-07-12
tags: [meta, build, pdf, pandoc, xelatex]
---

# `build/` · PDF 构建系统

> [← 返回目录](../README.md)  ·  [← 阅读版构建总说明](../阅读版构建.md)

---

## 这个目录里有什么

| 文件 | 作用 |
|---|---|
| `pdf-metadata.yaml` | Pandoc 元数据（title / author / geometry / ...）|
| `pdf-style.tex` | XeLaTeX preamble（字体 / 标题样式 / 代码块 / 页眉 / 链接色）|
| `build-pdf.sh` | PDF 构建脚本（主书版）|
| `build-site.sh` | MkDocs 站点构建脚本 |
| `README.md` | 本文档 |

---

## 为什么 PDF 拆成主书版

源 Markdown 有 **90+ 个文件**。全塞一个 PDF：

- 500+ 页，没人读完
- 构建 3+ 分钟
- PDF 查询体验反而不如在线站
- 字体嵌入后体积 20 MB+

**解法**：PDF 只做**主书版**——读者会从头到尾读的内容：
- 前言 + 引章
- 第一部分 · 处境与角色
- 第二部分 · 核心能力
- 第三部分 · 架构决策
- 第四部分 · 训练与落地（含 Unit 总览、Capstone、贯穿项目、周循环）
- 附录 A / E（工具）

**不塞 PDF 的**：
- **深入 01-19**（按需查的工程专题）
- **科学 01-04**（机制参考）
- **共同语言 01-05**（ML 术语表）
- **Unit 的 Week 详情**（执行手册属性，在线查更方便）
- **代码 GUIDE**（IDE 里看体验更好）
- **复习 / 维护**（日常工具，不是长阅读）

这些用**在线站点**阅读：`bash build/build-site.sh`。
也可以按需**各做一个专题卷 PDF**（见下方"按需专题卷"）。

---

## 一键构建（主书版 PDF）

```bash
bash build/build-pdf.sh
# 输出：output/AI时代的可靠性架构-v1.11.3.pdf
```

**改版本号**：
```bash
VERSION=v1.11.3 bash build/build-pdf.sh
```

---

## 依赖

### 必需

| 工具 | 作用 | 装法 |
|---|---|---|
| `pandoc` | Markdown → LaTeX → PDF 管道 | `brew install pandoc`（macOS）/ `apt install pandoc`（Ubuntu）|
| `xelatex` | LaTeX 引擎（CJK 友好）| 见下方 |

### XeLaTeX 安装

**macOS**（推荐）：
```bash
# 完整（~4 GB，一劳永逸）
brew install --cask mactex-no-gui

# 或极简（~100 MB，再按需加包）
brew install --cask basictex
sudo tlmgr update --self
sudo tlmgr install xecjk ctex fontspec titlesec booktabs mdframed \
                   framed enumitem fancyhdr xcolor hyperref longtable
```

**Ubuntu / Debian**：
```bash
sudo apt-get install -y \
  texlive-xetex \
  texlive-fonts-recommended \
  texlive-lang-chinese \
  texlive-latex-extra
```

**Windows**：装 [MiKTeX](https://miktex.org/) 或 [TeX Live](https://tug.org/texlive/)。

### 字体

**必需其一**（按 `pdf-style.tex` 里的 fallback 顺序）：

| 字体 | 覆盖 | 装法（macOS）|
|---|---|---|
| **Noto Serif CJK SC** + Noto Sans CJK SC | Google 免费首选 | `brew install --cask font-noto-serif-cjk-sc font-noto-sans-cjk-sc` |
| **Source Han Serif SC** + Source Han Sans SC | Adobe 开源 | `brew install --cask font-source-han-serif font-source-han-sans` |
| **Songti SC** + Heiti SC | macOS 系统自带 | 无需安装 |
| **PingFang SC** | macOS 系统自带 | 无需安装 |

**Ubuntu**：
```bash
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra
```

**验证**：
```bash
fc-list :lang=zh | head -5
```

---

## 缺字体怎么办

如果构建报 `! Package xeCJK Error: No Chinese font available` 或类似：

1. **首选**：按上方装 Noto CJK
2. **次选**：改 `pdf-style.tex` 里的 `\setCJKmainfont` 到你系统已有的字体：
   ```latex
   \setCJKmainfont{你系统里有的中文字体名}
   ```
   查你系统有什么字体：`fc-list :lang=zh`
3. **下策**：用 HTML → PDF 路径（见下方"备选方案"）

---

## 备选方案（装不了 LaTeX 时）

### 方案 B · MkDocs + Chrome 打印

```bash
bash build/build-site.sh
cd site && python -m http.server 8080
# 浏览器打开 http://localhost:8080
# 每章用 Ctrl/Cmd + P 打印为 PDF
```

**优点**：无 LaTeX 依赖
**缺点**：需要手动打印；分页控制弱；一章一个 PDF，不是合集

### 方案 C · MkDocs Material 的 PDF 插件

```bash
pip install mkdocs-with-pdf
# 在 mkdocs.yml 的 plugins 里加 with-pdf
# 跑 mkdocs build，输出 site/pdf/...
```

**缺点**：质量和 Pandoc + LaTeX 有差距；中文字体还是要配。

### 方案 D · Typst（未来方向）

[Typst](https://typst.app/) 是新兴排版引擎，CJK 支持好、编译快 10×。可以把 Markdown → Typst → PDF。需要额外写 Typst 模板，当前未实现。如果你愿意试，欢迎 PR。

---

## 按需专题卷（进阶）

想给"深入 / 科学 / 共同语言"也各出一份 PDF：**复制 `build-pdf.sh` → 改 `FILES` 数组 → 改 `OUTPUT_FILE`**：

```bash
cp build/build-pdf.sh build/build-pdf-deep.sh
# 编辑，把 FILES 改成 深入/*.md
# 跑：bash build/build-pdf-deep.sh
# 输出：output/AI时代的可靠性架构-v1.11.3-深入卷.pdf
```

同理做科学卷、共同语言卷、复习卷。每本 50-100 页较舒适。

---

## PDF 构建失败排查

| 症状 | 原因 | 解法 |
|---|---|---|
| `! Undefined control sequence` | LaTeX 包缺失 | `sudo tlmgr install <缺失包>` |
| `Package xeCJK Error: No Chinese font` | 字体缺失 | 装字体或改 `pdf-style.tex` |
| `Missing character` | Emoji / 特殊符号 LaTeX 不支持 | 源 MD 少用 emoji；或改 preamble 加 fallback |
| `Overfull \hbox` | 代码行 / 表格过宽（警告，不致命）| 忽略或在源里换行 |
| 构建卡住无输出 | TeX 在下载包（MiKTeX / basictex）| 等待或换完整 TeX 发行版 |
| `File 'xx.sty' not found` | 某 LaTeX 包没装 | `tlmgr install xx`（macOS / Linux）|

**单章调试**（精确定位哪章坏）：
```bash
pandoc 深入/03-模型与工具场景化最佳实践.md \
  --pdf-engine=xelatex \
  --include-in-header=build/pdf-style.tex \
  -o /tmp/test.pdf
```

---

## 本构建系统的设计原则

1. **源 Markdown 是唯一 authoritative**。PDF 是派生物，不手工编辑 PDF 去修 bug
2. **幂等**：同样输入 → 同样输出
3. **失败要响**：不静默，要打印清晰错误 + 修复建议
4. **合理裁剪**：主 PDF 只含阅读主线，不是"所有内容的堆砌"
5. **Vendor-neutral**：不锁定 TeX 发行版 / 字体厂商，通过 fallback 支持多环境

---

## 相关文档

- [阅读版构建总说明](../阅读版构建.md)（MkDocs + PDF 合并说明）
- [样式指南](../样式指南.md)（Markdown 写作规范——PDF 渲染最终回到这）
- [维护系统](../维护/README.md)（书的版本 / 更新节奏）

---

[← 返回目录](../README.md)
