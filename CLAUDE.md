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
│   ├── fanqie_publish.py  # 番茄小说发布（可选，需 Playwright）
│   ├── qidian_publish.py   # 起点小说发布（可选，需 Playwright）
│   └── qimao_publish.py    # 七猫小说发布（可选，需 Playwright）
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

### 质量门禁（八项）
每章必须通过：字数检查、开头抓力、章末钩子、AI味检测、冲突检测、标点规范、视角一致性、重复段落
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
6. `python3 scripts/quality_gate.py check -p <项目>` — 八项门禁

### 写后同步（自动执行，不许等用户催）
写完一章并门禁通过后，必须**自动**运行以下命令：
```bash
python3 scripts/story_graph.py -p <项目> post-write --chapter N
```

这条命令负责：
   - **自动写入知识图谱**：从 bible 提取角色/地点名，匹配正文后自动添加到 story_graph.json
   - **智能分类事件类型**：根据正文内容自动推断事件类型（不再写死 conflict_thrill）
   - 自动更新时间线（timeline.md）
   - 列出检查清单：属性变化？角色关系变化？伏笔？
   - 更新 state.json 的 `synced_up_to_chapter` 标记

### 写后发布（可选，需配置番茄/起点）
门禁通过 + post-write 完成后，检查 `state/current/state.json` 中的发布配置：

**番茄发布：**
检查 `fanqie.enabled` 和 `fanqie.auto_publish_after_gate`：
- **两者都为 true** → **自动**执行发布（不许等用户催，和 post-write 一样）
- **enabled=true 但 auto=false** → 用户说"发布到番茄"时才执行
- **enabled=false** → 完全跳过

**起点发布：**
检查 `qidian.enabled` 和 `qidian.auto_publish_after_gate`：
- **两者都为 true** → **自动**执行发布
- **enabled=true 但 auto=false** → 用户说"发布到起点"时才执行
- **enabled=false** → 完全跳过

**七猫发布：**
检查 `qimao.enabled` 和 `qimao.auto_publish_after_gate`：
- **两者都为 true** → **自动**执行发布
- **enabled=true 但 auto=false** → 用户说"发布到七猫"时才执行
- **enabled=false** → 完全跳过

发布命令：
```bash
# 番茄
python3 scripts/fanqie_publish.py upload -p <项目> --chapter N
python3 scripts/fanqie_publish.py upload -p <项目> --chapter N --force  # 跳过门禁检查强制上传

# 起点
python3 scripts/qidian_publish.py upload -p <项目> --chapter N
python3 scripts/qidian_publish.py upload -p <项目> --chapter N --force  # 跳过门禁检查强制上传

# 七猫
python3 scripts/qimao_publish.py upload -p <项目> --chapter N
python3 scripts/qimao_publish.py upload -p <项目> --chapter N --force  # 跳过门禁检查强制上传
python3 scripts/qimao_publish.py list-drafts -p <项目>   # 查看草稿箱并与本地状态对比
```

用户可用的提示词：
- **"发布到番茄"** → 上传最新已过门禁章节到番茄草稿箱
- **"发布到起点"** → 上传最新已过门禁章节到起点草稿箱
- **"发布到七猫"** → 上传最新已过门禁章节到七猫草稿箱
- **"番茄状态"** → 查看番茄上传状态
- **"起点状态"** → 查看起点上传状态
- **"七猫状态"** → 查看七猫上传状态
- **"七猫草稿箱"** → 查看七猫草稿箱并与本地记录对齐

降级策略（番茄、起点、七猫通用）：
- Playwright 未安装 → 跳过发布，提示用户手动操作
- 登录态过期 → 暂停发布，提示重新 login
- 上传失败 → 警告但**不阻断**写作流程，章节已保存在本地 manuscript/
- 未绑定 book_id → 跳过，提示用户确认 book_id

**注意：七猫严格禁止重复内容，每次上传必须先清空再填新内容，一次只传一章，出错即停，不批量。**

首次配置：
```bash
# 番茄
pip install playwright && playwright install chromium
python3 scripts/fanqie_publish.py setup               # 安装 + 登录
# 然后在 state.json 中设置 fanqie.enabled=true, fanqie.auto_publish_after_gate=true

# 起点
pip install playwright && playwright install chromium
python3 scripts/qidian_publish.py login                # 登录（起点不支持账密，仅手机验证码）
# 然后在 state.json 中设置 qidian.enabled=true, qidian.auto_publish_after_gate=true
# 注意：起点 book_id 需要用户在 URL 中获取，格式：https://write.qq.com/.../CBID/{book_id}/...

# 七猫
pip install playwright && playwright install chromium
python3 scripts/qimao_publish.py login                # 登录（七猫不支持账密，仅手机验证码）
# 然后在 state.json 中设置 qimao.enabled=true, qimao.auto_publish_after_gate=true
# 七猫 book_id：11901780
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

## 起点发布状态
- `state/qidian-publish-state.json` 记录已上传章节（book_id 内置为 35730802204107809）
- `~/.novel-master/qidian-auth-state.json` 保存浏览器登录态
- 发布命令：`python3 scripts/qidian_publish.py upload -p <项目> --chapter N`
- 查看状态：`python3 scripts/qidian_publish.py status -p <项目>`

## 七猫发布规则（铁律）

七猫发布有严格的内容检测，**绝对不能有重复内容**。

### 操作规则
1. **上传前必须清空** - 每次进入上传页面，必须先用 `fill("")` 两次清空标题和正文，再填入新内容
2. **单章操作** - 每次只上传一章，上传成功后再操作下一章
3. **出错即停** - 任何一步失败立即停止，不继续上传后续章节
4. **不批量** - 七猫禁止批量操作，必须一章一章单独上传

### 章节号规则
- 草稿箱的章节号是**自动按上传顺序排**的，定不了也改不了
- 如果章号传错了 → 从草稿箱**删除那个章节** → 重新上传正确的章号
- **不能换书**，书创建后就不能换绑

### 技术要点
- 两次 `fill("")` 清空编辑器是必须的，不能省
- 每次点击保存后弹窗有5秒倒计时，按钮 `disabled` 消失后才能点击"我已阅读并知晓"确认
- 当前 book_id：`11901780`

### 命令
- 登录：`python3 scripts/qimao_publish.py login`
- 上传：`python3 scripts/qimao_publish.py upload -p <项目> --chapter N`
- 状态：`python3 scripts/qimao_publish.py status -p <项目>`
- 查看草稿箱对比：`python3 scripts/qimao_publish.py list-drafts -p <项目>`

## 门禁修复规则（重要）

### 一次性修复原则
门禁失败后修复章节时，**必须一次性修完所有问题**，禁止分轮修复（先修AI味、再修字数、再修破折号）。

修复步骤：
1. 先跑 `quality_gate.py check` 看全部问题
2. 在**同一次编辑**中修完所有 fail/warn 项
3. 修复时**只改有问题的部分**，不要大面积重写或删减
4. 修完后再跑一次门禁验证

### 修复红线
- **禁止砍内容来修AI味** — 删掉「像是」不代表要把整段描写删了
- **禁止凑字数** — 铁律是写前规划好内容量，不事后补
- **修AI味 = 替换而非删除** — 把"仿佛凝固"改成具体描写，不是删掉整句

### 批量检查
一次性检查多章（一次 Python 进程，避免多次启动开销）：
```bash
python3 scripts/quality_gate.py batch -p <项目>
python3 scripts/quality_gate.py batch -p <项目> --chapter 5  # 从第5章开始
```

## 记忆系统（防跑偏）

### 写作简报（写前必读）
```bash
python3 scripts/story_graph.py -p <项目> brief --chapter N
```
自动汇集：项目进度、**本章章纲**、最近事件（timeline+state合并）、活跃冲突、待解伏笔、**最近登场角色**（按登场章排序，最多10个）、地点、节奏建议。断连后回来先跑这个。

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
