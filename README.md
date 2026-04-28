# Novel Master — 小说创作系统

综合小说创作系统，整合了工程流程、手艺知识库、一致性保障、去AI味四大维度。支持从选题诊断到完稿校验的全流程。

## 安装（作为 Claude Code Skill）

```bash
# 1. 克隆仓库
git clone git@github.com:WGL878420/novel-master.git

# 2. 创建软链接到 Claude Code 技能目录
ln -s $(pwd)/novel-master ~/.claude/skills/novel-master
```

安装后在 Claude Code 中触发关键词 `写小说`、`创作故事`、`novel` 即可使用。

### 验证是否安装成功

```bash
ls -la ~/.claude/skills/novel-master/
# 应能看到 SKILL.md、CLAUDE.md、scripts/ 等文件
```

### 更新技能

```bash
cd novel-master && git pull
```

### 卸载

```bash
rm ~/.claude/skills/novel-master     # 删除软链接
# 仓库目录保留，可手动删除
```

## 快速开始

```bash
# 全新创作 — 在 Claude Code 中
novel 我想写一本穿越题材的悬疑小说

# 或者初始化项目后手动写作
python3 scripts/init_project.py --name 我的小说 --genre 悬疑
python3 scripts/story_graph.py -p ./我的小说 extend-outline --count 20
```

## 功能

- **七阶段流程**：选题诊断 → 三层问答 → 结构规划 → 知识库初始化 → 写作执行 → 校验修复
- **去AI味检测**：7类24种模式检测，量化评分
- **质量门禁**：字数检查、开头抓力、章末钩子、AI味、冲突检测五步闭环
- **知识图谱**：角色/地点/事件图谱，连续性检查，伏笔追踪
- **事件矩阵**：节奏冷却跟踪，避免连续平淡章节
- **语料库检索**：基于 embedding 的相似场景检索
- **番茄平台适配**：爬取自官方作家课堂 131 篇教程的开篇法则/节奏框架/避坑指南

## 项目结构

```
novel-system/
├── SKILL.md                       # Claude Code 技能入口
├── CLAUDE.md                      # 项目级规则
├── scripts/                       # CLI 工具
│   ├── init_project.py            # 初始化新项目
│   ├── quality_gate.py            # 质量门禁检查
│   ├── anti_ai_detector.py        # AI味检测
│   ├── story_graph.py             # 知识图谱
│   ├── event_matrix.py            # 事件矩阵
│   ├── search_corpus.py           # 语料库搜索
│   └── utils.py                   # 共享工具
├── references/
│   ├── guides/                    # 14 份写作指南
│   └── flows/                     # 7 份阶段流程 + 基础设施
├── corpus/                        # 语料库
├── templates/                     # 项目模板
└── demo/                          # 示例项目
```

## 手动写作流程

```bash
# 写前准备
python3 scripts/story_graph.py -p <项目> brief --chapter N    # 最新状态简报
python3 scripts/story_graph.py -p <项目> check-continuity     # 连续性检查

# 写后同步
python3 scripts/quality_gate.py check -p <项目>              # 质量门禁
python3 scripts/story_graph.py -p <项目> post-write --chapter N  # 同步状态

# 扩展大纲
python3 scripts/story_graph.py -p <项目> extend-outline --count 20
```

## 致谢

整合自以下开源项目：
- [PenglongHuang/novel-creator-skill](https://github.com/PenglongHuang/novel-creator-skill)
- [Tomsawyerhu/chinese-novelist-skill](https://github.com/Tomsawyerhu/chinese-novelist-skill)
- [leenbj/Claude-Book](https://github.com/leenbj/Claude-Book)
- [oh-story](https://github.com/oh-story)
- [Humanizer-zh](https://github.com/Humanizer-zh)
