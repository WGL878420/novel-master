# Novel Master — 小说创作系统

## 项目结构
```
novel-master/
├── scripts/         # CLI 工具
│   ├── init_project.py    # 初始化新项目
│   ├── quality_gate.py    # 质量门禁检查
│   ├── anti_ai_detector.py # AI味检测
│   ├── story_graph.py     # 知识图谱
│   ├── event_matrix.py    # 事件节奏
│   ├── search_corpus.py   # 语料库
│   └── fanqie_publish.py  # 番茄小说发布（可选，需 Playwright）
├── references/
│   ├── guides/            # 写作指南
│   │   ├── chapter-craft.md   # 章节工艺（含字数规则）
│   │   ├── anti-ai-flavor.md  # 去AI味指南（含五层技法）
│   │   ├── anti-ai-flavor-rules.md  # 去AI味自查规则清单（七类速查表）
│   │   ├── fanqie-platform-writing.md  # 番茄平台写作指南（开篇法则/节奏框架/坑点）
│   │   └── short-story-writing.md  # 番茄短故事创作指南（悬疑/宫斗宅斗/脑洞/世情/年代/男频）
│   └── flows/             # 工作流
├── templates/             # 项目模板
├── corpus/                # 语料库
└── demo/                  # 项目实例
```

## 断连恢复铁律（重要）
断连后重新开始写之前，必须自动执行（不许等用户提醒）：
```bash
python3 scripts/story_graph.py -p <项目路径> brief --chapter <下一章编号>
```
先跑 brief 确认当前状态，再动笔。这是非协商规则。

## 核心规则

### 字数门禁（铁律）
- **每章 3000-3500 字**（全阶段统一，番茄/短篇/中篇/长篇各有配置）
- **铁律：一次性写满，绝不事后补字数**
- 开写前先确认内容量够撑满目标（目标3500，按3800规划）
- 字数不够 → 删掉整章重新写，不允许补充
- **重写时让剧情往前走**，不在原地加描写凑字数（扩描写 = 废话）
- quality_gate 字数检查不通过时返回非零退出码，不保存门禁记录

### 质量门禁（五步）
每章必须通过：字数检查、开头抓力、章末钩子、AI味检测、冲突检测
运行：`python3 scripts/quality_gate.py check -p <项目路径>`

### 去AI味
- 七类检测 + 五层技法（叙事逻辑/对话交互/感官描写/人物塑造/句式节奏）
- 目标密度：< 3.0/千字
- 检测：`python3 scripts/anti_ai_detector.py report <文件路径>`

### 番茄平台写作铁律（爬取自官方作家课堂131篇教程）
- **开篇三要**：3000字内完成立人设、亮金手指、抛冲突
- **开篇三不要**：不堆设定、不人物扎堆（≤5人）、不秀文笔
- **黄金三秒**：第一段就下钩子，300字内进主题，每字保证功能性
- **不存在过渡章**：过渡章 = 制造下一个期待感的铺垫过程，必须加入期待感/危机感/信息差
- **冲突设计**：双方必须有"不能退让的理由"，问"主角不这么做会失去什么"
- **人物活人感**：填过往（行为有逻辑）+ 加细节（动作神态）+ 添成长（合理蜕变）
- **爽点多样化**：打脸/升级/智斗/逆袭/情感多种搭配，避免单一
- **章末必留钩子**，每章至少一个小爽点/信息增量，连续2章平淡则第3章必须有爆点
- **高潮后遗症**：高潮后1-2章必须写高潮带来的改变（主线推进、人设成长、世界关系变化）
- **开篇不留人 = 无曝光**，番茄推荐机制以开头留存率为核心指标
- 完整版（含各品类创作宝典、避雷大全）见 `references/guides/fanqie-platform-writing.md`（131篇爬取汇总）

## 完整写作循环

### 写前准备（自动）
写新一章之前自动执行（不许等用户催）：
```bash
python3 scripts/story_graph.py -p <项目> brief --chapter N
python3 scripts/story_graph.py -p <项目> check-continuity
```

同时检查 `bible/03-outline.md` 确认当前章节位置。章纲只剩 ≤3 章 → 先 `extend-outline --count 20` 再写。

### 写一章
5. 按 3000-3500 字一次性写成
6. `python3 scripts/quality_gate.py check -p <项目>` — 五步门禁

### 写后同步（自动执行，不许等用户催）
写完一章并门禁通过后，必须**自动**运行以下命令：
```bash
python3 scripts/story_graph.py -p <项目> post-write --chapter N
```

这条命令负责：
   - 自动更新时间线（timeline.md）
   - 自动同步事件矩阵
   - 列出检查清单：新角色？新地点？属性变化？伏笔？
   - 更新 state.json 的 `synced_up_to_chapter` 标记

### 写后发布（可选，需配置番茄）
门禁通过 + post-write 完成后，检查 `state/current/state.json` 中 `fanqie.enabled` 和 `fanqie.auto_publish_after_gate`：
- **两者都为 true** → **自动**执行发布（不许等用户催，和 post-write 一样）
- **enabled=true 但 auto=false** → 用户说"发布到番茄"时才执行
- **enabled=false** → 完全跳过

发布命令：
```bash
python3 scripts/fanqie_publish.py upload -p <项目> --chapter N --mode draft
```

用户可用的提示词：
- **"发布到番茄"** → 上传最新已过门禁章节到草稿箱
- **"发布到番茄 1-10"** → 批量上传第1-10章
- **"设置番茄发布"** → 首次配置（引导 setup + login + create-book）
- **"番茄状态"** → 查看上传状态
- **"番茄书籍列表"** → 列出作家后台书籍

降级策略：
- Playwright 未安装 → 跳过发布，提示用户手动操作
- 登录态过期 → 暂停发布，提示 `python3 scripts/fanqie_publish.py login`
- 上传失败 → 警告但**不阻断**写作流程，章节已保存在本地 manuscript/
- 未绑定 book_id → 跳过，提示用户先运行 `fanqie_publish.py setup` + `create-book`

首次配置：
```bash
pip install playwright && playwright install chromium
python3 scripts/fanqie_publish.py setup               # 安装 + 登录
python3 scripts/fanqie_publish.py create-book -t "书名" -g 玄幻 -s "简介" -p <项目>  # 创建书并绑定
# 然后在 state.json 中设置 fanqie.enabled=true, fanqie.auto_publish_after_gate=true
```

### 检查
9. 定期运行 `python3 scripts/story_graph.py -p <项目> check-bible` — 检查 bible 填写完整度
10. 定期运行 `python3 scripts/story_graph.py -p <项目> sync-status` — 同步状态总览
11. **章纲不够用了？** → `extend-outline --count 20`

### 初始项目生成注意
- `init_project.py` 现在会生成**有内容的 bible**，不再是空字段
- 角色档案中姓名仍为（待定），需自行设定
- 每写一章必须同步，否则 brief 会警告

## 同步状态标志
- `state.json` 中的 `synced_up_to_chapter` 记录已同步到第几章
- brief 自动检查：有未同步章节 → 红色警告
- post-write 自动更新时间线、事件矩阵、同步标记
- sync-status 总览：已写/已同步/timeline条目/图谱节点/大纲余量

## 番茄发布状态
- `state/fanqie-publish-state.json` 记录已上传章节和绑定的 book_id
- `state/fanqie-auth-state.json`（或 `~/.novel-master/`）保存浏览器登录态
- 发布命令：`python3 scripts/fanqie_publish.py upload -p <项目> --chapter N`
- 查看状态：`python3 scripts/fanqie_publish.py status -p <项目>`

## 记忆系统（防跑偏）

### 写作简报（写前必读）
```bash
python3 scripts/story_graph.py -p <项目> brief --chapter N
```
自动汇集：项目进度、最近事件、活跃冲突、待解伏笔、角色当前属性、地点、节奏建议。断连后回来先跑这个。

### 属性追踪（防矛盾）
```bash
# 记录角色/地点的状态变化
python3 scripts/story_graph.py -p <项目> add-attr --id <节点ID> --key <属性名> --value <属性值> --chapter N

# 如果与前文矛盾会自动警告
```

### 连续性检查
```bash
python3 scripts/story_graph.py -p <项目> check-continuity
```
检查三项：属性矛盾（同一key在不同章节值不同）、伏笔超期（25章未解）、悬空边。

### 章节扩展
```bash
# 写到初始规划的末尾了，再追加 N 行章纲（自动填充三幕骨架）
python3 scripts/story_graph.py -p <项目> extend-outline --count 20

# 更新目标章节估算
python3 scripts/story_graph.py -p <项目> update-estimate --chapters 100
```
`extend-outline` 自动判断当前处于第几幕，按对应模板填充（每4种模式轮换），避免千篇一律。章名和具体内容手动编辑 `bible/03-outline.md` 即可。

## 章节数规则
- **不设上限** — 初始大纲只生成~15章骨架，写完后随时扩展
- `estimated_chapters` 只是估算值，不限制实际写作
- 质量门禁、事件矩阵、伏笔追踪均不受章节数限制
