---
name: novel-master
description: |
  综合小说创作系统。整合了工程流程(PenglongHuang)、手艺知识库(Tomsawyerhu + oh-story)、一致性保障(leenbj + Claude-Book)、去AI味(Humanizer-zh)四大维度。
  支持从选题诊断到完稿校验的全流程，内置语料检索、知识图谱、事件矩阵、质量门禁等机制。
  触发关键词：写小说、创作故事、长篇写作、网文创作
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# Novel Master: 综合小说创作系统

## 路径约定

本文档中 `{skill_dir}` 指本 SKILL.md 所在的目录（即 novel-system 的根目录）。

## 安装

```bash
# 1. 克隆仓库
git clone git@github.com:<your-username>/novel-system.git

# 2. 创建软链接到 Claude Code 技能目录
ln -s $(pwd)/novel-system ~/.claude/skills/novel-master

# 3. 验证
claude "写小说"  # 应触发 novel-master 技能
```

更新技能：在 `{skill_dir}` 目录下 `git pull origin main` 即可。

## 核心原则

### 三条铁律
1. **冲突驱动剧情** — 每章必须有冲突或转折，无冲突不落笔
2. **悬念承上启下** — 每章结尾必须留下钩子，章末不散劲
3. **展示而非讲述** — 用动作和对话表现，不用抽象总结，AI 味是硬伤

### 三层质量观
- **选题层**：这个点子值不值得写、有没有卖点、能不能持续
- **执行层**：每章有目标、有冲突、有变化、有余韵
- **一致层**：人物不漂、伏笔有收、世界观不崩、时间线不乱

### 五大约束
1. 每章必须完成质量门禁闭环才能进入下一章
2. 非终章禁止解决核心冲突，每章必须增加至少1个新未解决问题
3. 禁止在正文中混入元数据（`[说明]`、`TODO`、思考过程等）
4. 门禁失败时唯一合法操作是修复本章
5. 主线修改必须经过明确的大纲变更流程

---

## 七阶段总览

| 阶段 | 名称 | 产出 | 参考文件 |
|------|------|------|---------|
| Phase 0 | 初始化 | 加载偏好、检测未完成项目 | `{skill_dir}/references/flows/phase0-init.md` |
| Phase 1 | 选题与诊断 | 题材诊断书、卖点评估 | `{skill_dir}/references/flows/phase1-selection.md` |
| Phase 2 | 三层问答 | 核心定位、深度定制、标题 | `{skill_dir}/references/flows/phase2-qa.md` |
| Phase 3 | 结构规划 | 大纲、人物档案、写作计划JSON | `{skill_dir}/references/flows/phase3-planning.md` |
| Phase 4 | 知识库初始化 | bible/ + state/ + 知识图谱 | `{skill_dir}/references/flows/phase4-kb-init.md` |
| Phase 5 | 写作执行 | 逐章正文 | `{skill_dir}/references/flows/phase5-writing.md` |
| Phase 6 | 校验与修复 | 门禁报告、修复版本 | `{skill_dir}/references/flows/phase6-validation.md` |

详见各阶段流程文档。

---

## 写作模式

进入 Phase 5 时选择：

| 模式 | 适用场景 | 说明 |
|------|---------|------|
| **串行 (serial)** | 默认推荐 | 主 Agent 逐章写，稳定可控 |
| **并行 (parallel)** | 速度优先 | 子 Agent 分批并行，需写作计划JSON协调 |
| **审查模式 (review)** | 质量优先 | 每章写后自动触发多Agent交叉审 |

---

## 内置脚本

```bash
python3 {skill_dir}/scripts/init_project.py      # 创建新项目结构
python3 {skill_dir}/scripts/event_matrix.py      # 事件矩阵管理（冷却跟踪）
python3 {skill_dir}/scripts/story_graph.py       # 知识图谱维护
python3 {skill_dir}/scripts/quality_gate.py      # 质量门禁检查
python3 {skill_dir}/scripts/anti_ai_detector.py  # AI味检测
python3 {skill_dir}/scripts/search_corpus.py     # 语料库检索
```

---

## 手艺指南速查

| 指南 | 解决的问题 |
|------|-----------|
| `{skill_dir}/references/guides/story-structures.md` | 选什么结构？三幕/英雄之旅/悬疑/言情/多线 |
| `{skill_dir}/references/guides/hook-techniques.md` | 章末怎么留人？13种钩子技法 |
| `{skill_dir}/references/guides/dialogue-writing.md` | 对白怎么写才不假？ |
| `{skill_dir}/references/guides/character-building.md` | 人物怎么设才不工具人？ |
| `{skill_dir}/references/guides/anti-ai-flavor.md` | 文字有AI味怎么办？7类检测+两遍润色 |
| `{skill_dir}/references/guides/chapter-craft.md` | 每章怎么写？开头/中段/后段/结尾 |
| `{skill_dir}/references/guides/emotion-design.md` | 情绪怎么调动读者？6种情绪弧线 |
| `{skill_dir}/references/guides/plot-engineering.md` | 情节怎么不散？事件矩阵+反转工具箱 |
| `{skill_dir}/references/guides/opening-techniques.md` | 开头怎么抓人？8种开局模板 |

---

## 项目目录结构

```
{project-name}/
├── bible/                         # 永久不变（风格/角色/世界观）
│   ├── 00-world-building.md       # 世界观设定
│   ├── 01-character-profiles.md   # 角色档案
│   ├── 02-style-guide.md          # 风格指南
│   ├── 03-outline.md              # 大纲（含分卷+章纲）
│   └── 04-research.md             # 研究资料
├── state/                         # 每章更新的运行时状态
│   ├── current/                   # 当前状态（指向最新章）
│   ├── chapter-NN/                # 每章状态快照
│   └── template/                  # 初始状态模板
├── manuscript/                    # 正文章节
│   ├── 第001章-{title}.md
│   └── 第002章-{title}.md
├── knowledge/                     # 结构化知识
│   ├── story_graph.json           # 知识图谱
│   ├── event_matrix.json          # 事件矩阵
│   └── timeline.md                # 时间线
└── gates/                         # 门禁检查记录
    └── 第001章-gate.json
```

---

## 启动命令

```bash
# 全新创作
novel 我想写一本{题材}小说，{简要描述}

# 继续创作
novel 继续写
novel 继续写 "主角在朝堂上首次发言"

# 修复
novel 修复本章

# 中途改纲
novel 改纲续写
```

---

## 项目级规则

写作流程的完整规则（字数门禁、质量门禁五步、去AI味七类检测、番茄平台铁律、记忆系统、同步流程）定义在项目 `CLAUDE.md` 中，`init_project.py` 生成新项目时会自动创建。技能启动后通过 Read 加载项目根目录的 `CLAUDE.md` 来获取规则。
