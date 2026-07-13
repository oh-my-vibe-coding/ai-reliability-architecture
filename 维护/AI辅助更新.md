---
title: AI 辅助更新 · 让 Claude Code 帮你维护书
updated: 2026-05-24
tags: [meta, maintenance, ai-assisted, prompts]
---

# AI 辅助更新 · 让 Claude Code 帮你维护书

> [← 维护系统](README.md)

> [!NOTE]
> **这是一本讲 AI 的书，维护也该用 AI**。下面给出**可直接复制**的 prompt，让 Claude Code（或 Cursor / Codex CLI）帮你完成 60-80% 的月度更新工作量。
>
> **但记住**：**不能让 AI 独自更新**——这就踩了书反复强调的坑（[深入 09 · 何时不该用 AI](../深入/09-何时不该用AI.md) 的反模式）。AI 当建议者，你当决策者。

---

## 1. 三种协作模式

| 模式 | 谁做什么 | 适合 |
|---|---|---|
| **AI 调研 + 人工决策** | AI 扫描、总结变化；你选哪些进书 | 月度 patch |
| **AI 起草 + 人工改写** | AI 写初稿，你按 B2 方式挑错改写 | 新章节 / 大改 |
| **AI 全自动** | AI 自行更新并 commit | ❌ **不推荐** |

**永远走前两种**。

---

## 2. 月度更新 · 标准 Prompt

复制以下 prompt 到 Claude Code（在项目根目录运行）：

````markdown
你正在帮我维护《AI 时代的可靠性架构》这本书的月度更新。

请完成以下工作，**但不要直接修改任何文件**——只生成建议清单让我 review：

## 任务

### 1. 模型榜单扫描
访问以下来源（用 WebFetch 或 WebSearch），对比书里 `深入/03-模型与工具场景化最佳实践.md` 的相应部分：

- LM Arena: https://arena.ai/leaderboard
  - 给 Overall Top 10 和 Coding Top 5 当前状态
- OpenRouter: https://openrouter.ai/rankings
  - 给付费模型 Token 用量 Top 10
- SWE-bench Verified: https://www.swebench.com/verified.html
  - 给 Top 5

对每项标注：
- 和书里的差异
- 建议的更新文字（markdown 片段）

### 2. 厂商新模型扫描
对这些 docs 做检查：
- https://platform.claude.com/docs/en/docs/about-claude/models
- https://platform.openai.com/docs/models  
- https://ai.google.dev/gemini-api/docs/models
- https://api-docs.deepseek.com/

有没有书里没列出的模型？或定价/context 变化？

### 3. 链接存活扫描
对 `附录/B-参考文献.md` 里的 URL 抽样 10 个做 HEAD 请求，报告失效的。

### 4. 生成建议清单
在 `/tmp/monthly-update-YYYY-MM.md` 文件里生成以下结构的建议：

```markdown
# 月度更新建议 YYYY-MM

## 强烈建议更新（重要变化）
- [具体文件 + 具体行 + 变更文字]

## 建议更新（一般变化）
- [...]

## 发现但建议不动（噪声 / 已 deprecated）
- [...]

## 未能验证（要人工看）
- [带理由，如 "页面需要登录"]
```

## 边界（不要做）
- ❌ 不要直接改书的任何文件
- ❌ 不要更新 CHANGELOG
- ❌ 不要 bump 版本号
- ❌ 不要 git commit

这些都由我人工做。
````

**用法**：
1. 把 prompt 贴给 Claude Code
2. 等它生成建议清单（通常 3-5 分钟）
3. 自己过清单，选可接受的改动
4. 按 [月度更新清单](月度更新清单.md) 手动更新

**成本**：大约 $0.5-1 的 API 费用（取决于模型）。

---

## 3. 新章节起草 · 标准 Prompt

```markdown
我要为《AI 时代的可靠性架构》写一篇新章节，主题是 [X]。

**阅读以下文件了解书的风格**：
- `/path/to/样式指南.md`（排版规范）
- `/path/to/深入/01-首包延迟与吞吐的影响因素.md`（同类风格参考）
- `/path/to/深入/09-何时不该用AI.md`（同类风格参考）

**新章节目标**：[具体目标]

**约束**：
- SRE 架构师视角，不是 ML 研究员视角
- 工程:科学 ~70:30
- ~300-500 行
- 必须包含：frontmatter、一级标题只有 1 个、GitHub-style callouts、导航页脚、参考资料
- 每节必有 "SRE 能做什么"
- 结尾必有 "给 SRE 的一句话总结"

**输出位置**：先写到 `/tmp/draft-X.md`，不要直接落在书里。

**不要做**：
- 不要加进主 README 的目录（我人工加）
- 不要写 CHANGELOG 条目（我写）
```

**用法**：
1. AI 给出 draft
2. 你用 B2 方式改写（不是让 AI 再改，你改）
3. 改到满意了再 copy 到书的目录
4. 自己更新 README、CHANGELOG、相关 cross-link

---

## 4. Pattern 捞取 · 事故库扩充 Prompt

针对 [深入 10 · AI 系统事故模式库](../深入/10-AI系统事故模式库.md)：

```markdown
请扫描以下来源，找出本季度（YYYY Q-）公开的 AI 系统事故，归纳是否属于 `深入/10-AI系统事故模式库.md` 里已有的 Pattern 1-15：

- https://www.anthropic.com/news （所有 postmortem 类博客）
- https://status.openai.com/history （事故后的 detailed postmortem）
- 各推理服务 provider 的 status page
- HackerNews 搜 "LLM outage" "AI postmortem"
- arXiv 搜 "failure modes in LLM"

对每个事故：
1. 一句话描述
2. 匹配已有 Pattern？还是**新 pattern**？
3. 如果是新 pattern，按书里的模板起草一个 Pattern N（症状/根因/检测/处置/预防）

输出到 `/tmp/new-patterns.md`。
```

---

## 5. 术语表自动扩充

针对 [附录/C-术语表.md](../附录/C-术语表.md)：

```markdown
扫描这本书所有章节，找出以下情况的术语：

1. 在多个章节出现但 `附录/C-术语表.md` 里没有的
2. 已过期或定义有变的

生成补充列表（不要直接改文件），包含：
- 术语 / 含义 / 首次出现章节
```

---

## 6. Cross-link 一致性检查

```markdown
扫描整本书的内部链接（形如 `[文本](../X/Y.md)` 和 `[文本](X/Y.md)`），报告：

1. 死链（文件不存在）
2. 链到的锚点不存在
3. 过时的章节名（和当前 title 不匹配）

以文件为单位输出，不要直接修复。
```

---

## 7. 样式一致性检查

```markdown
检查所有 .md 文件是否符合 `样式指南.md`：

1. 有无 frontmatter
2. H1 只有一个
3. Callout 是否用 [!NOTE/TIP/...] 形式
4. 代码块是否都有语言标签
5. 导航页脚是否在底部

生成违规清单，不要直接改。
```

---

## 8. AI 辅助的"不要"清单

> [!WARNING]
> 以下事情**不要**让 AI 做，即使它能做：

- ❌ **直接 commit 到主分支**：应该 PR review
- ❌ **决定什么值得加进书**：书的定位是架构师的判断
- ❌ **写 CHANGELOG 的"本季度关键趋势"总结**：需要人类视角
- ❌ **删除章节**：要有人判断是否真的过时
- ❌ **重写 B2 产物为它觉得更好的版本**：违反 B2 训练原则
- ❌ **自动跑循环**（per cron job 持续更新）：失去人类 review 环节

---

## 9. 协同节奏建议

**个人维护者**：
- 月度：用 Prompt 1，人工决策
- 季度：用 Prompt 2/4/5/6/7 之一（按需）
- 年度：大改需要人工主导，AI 辅助

**团队维护**：
- 一个人跑 AI prompts 生成建议
- 另一个人做决策 review
- 第三个人 merge

---

## 10. 元启示

这一章本身是 **"AI 时代的 SRE 架构师"** 的实战示范：
- 明确**定义 AI 的工作范围**（[第 6 章 · 致命三角](../知识/06-AI自治与上下文架构约束.md)）
- 明确**什么不让 AI 做**（[深入 09](../深入/09-何时不该用AI.md)）
- 明确**人类保留什么判断权**
- 有**审计日志**（CHANGELOG）
- 有**多轮验证**（[深入 10 · Pattern 5 Tool Poisoning](../深入/10-AI系统事故模式库.md)）

**用书里讲的原则来维护书自身**——这就是系统一致性。

---

[← 维护系统](README.md)  ·  [📖 总目录](../README.md)
