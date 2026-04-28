# Phase 5: 写作执行

## 目标
按照大纲逐章创作，每章完成质量门禁后进入下一章。

## 核心约束
1. 每章必须完成质量门禁闭环才能进入下一章
2. 非终章禁止解决核心冲突，每章必须增加至少1个新未解决问题
3. 禁止在正文中混入元数据
4. 门禁失败时唯一合法操作是修复本章

## 写作模式

### 模式1: 串行（serial，默认）
主 Agent 逐章写，每章完成门禁后继续下一章。

### 模式2: 并行（parallel，速度优先）
- 将章节分成批次（每批3-5章）
- 派生子 Agent 并行写作
- 通过 `02-写作计划.json` 协调状态
- 适用于熟悉写作流程后的提速

### 模式3: 审查模式（review，质量优先）
- 每章写完后自动触发多Agent交叉审
- 审核维度：逻辑一致性、阅读体验、去AI味
- 最多3轮修复

## 每章写作流程

### Step 1: 预读
写作前必读：
1. `bible/03-outline.md` 中本章的章纲
2. `state/current/state.json`（当前故事状态）
3. `bible/01-character-profiles.md`（人物档案，快速确认）
4. `knowledge/timeline.md`（时间线确认）

### Step 2: 语料检索（可选）
如果本章涉及特定类型（如开头、对白、章末钩子），先用脚本搜索相似范本：
```bash
python3 scripts/search_corpus.py search-type --type "高张力对白" --limit 3
python3 scripts/search_corpus.py search-keyword --keyword "弹幕" --limit 5
```

### Step 3: 事件类型选择
使用事件矩阵推荐本章事件类型：
```bash
python3 scripts/event_matrix.py suggest
```

### Step 4: 章节写作
使用 [chapter-craft.md](../guides/chapter-craft.md) 的指导：

**标准章结构：**
```
开头(15%)：抓手，迅速进入场景
中段(50%)：推进，冲突升级或新信息出现
后段(25%)：变化，局面发生实质性改变
结尾(10%)：拉力，留下继续阅读的理由
```

**写作时强制遵守：**
- ✅ 开头300字内建立场景和冲突
- ✅ 每场戏有目标、有阻碍、有变化
- ✅ 用动作和对话推进，反对抽象总结
- ✅ 章末留钩子（参考 [hook-techniques.md](../guides/hook-techniques.md)）
- ✅ 保持人物语言个性化
- ❌ 不在正文中讲设定
- ❌ 不用「空气仿佛凝固」等AI套话
- ❌ 不用「她感到/他内心」等情绪解释

### Step 5: 去AI味自查
写作完成后，运行检测：
```bash
python3 scripts/anti_ai_detector.py report manuscript/第xxx章-xxx.md
```

如密度超标，按 [anti-ai-flavor.md](../guides/anti-ai-flavor.md) 的「两遍润色法」修复。

### Step 6: 质量门禁
```bash
python3 scripts/quality_gate.py check
```

门禁五项：
| 检查项 | 通过标准 |
|--------|---------|
| 字数 | 2000-6000字 |
| 开头抓力 | 前300字有对话/动作/冲突之一 |
| 章末钩子 | 结尾有疑问/转折/中断之一 |
| AI味密度 | < 3/千字 |
| 冲突 | 不少于3个冲突词 |

### Step 7: 更新状态
门禁通过后：
1. 将当前 state 快照到 `state/chapter-NN/`
2. 更新 `knowledge/timeline.md`
3. 更新知识图谱（添加新节点/关系）
4. 记录事件矩阵
5. 更新 state/current/ 为最新状态

## 写入规范
- 每章 3000-5000 字
- 文件命名：`第001章-章名.md`
- 格式：标准 Markdown
- 正文标题用 `##` 或 `###`

## 特殊情况

### 中断续写
如写作中断，下次启动时：
1. 读取 `state/current/state.json`
2. 读取最新完成的章节
3. 重新生成续写方向建议
4. 用户确认后继续

### 偏离大纲
如写作过程中发现大纲需要调整：
1. 暂停当前章节
2. 使用 `/改纲续写` 流程
3. 更新 `bible/03-outline.md`
4. 级联更新知识图谱
5. 继续写作

## 参考
- 每章工艺：Tomsawyerhu 的「逐章写作」+ oh-story「长篇写作」
- 语料检索：Tomsawyerhu 的 corpus 系统
- 门禁机制：leenbj 的 5-step gate + Claude-Book 的多Agent审查
- 事件矩阵：leenbj 的事件冷却
