# 共享机制

跨阶段共享的系统和规则。

## 偏好系统

### 存储位置
`~/.claude/skills/china-novelist/user-preferences.json`

### 自动学习的内容
- 常用题材
- 常用章节数
- 写作模式偏好（串行/并行）
- 常见风格选项
- 去AI味强度（宽松/标准/严格）

### 更新时机
每次完成一个项目后更新。

## 黄金法则详解

### 法则1: 展示而非讲述
| ❌ 不要 | ✅ 要 |
|---------|------|
| 她心中五味杂陈 | 她张了张嘴，最后只把手里的杯子放回桌上 |
| 他很危险 | 他没抬高声音，屋里就安静了 |
| 气氛非常微妙 | 她说完那句话后，他没有接 |

### 法则2: 冲突驱动剧情
- 每章必须包含冲突或转折
- 冲突类型：对抗/困境/抉择/秘密揭示/关系变化
- 无冲突的场景默认删、并、压缩

### 法则3: 悬念承上启下
- 每章结尾必须有钩子
- 钩子类型：突然揭示/紧急危机/未完成动作/身份反转/两难选择
- 详见 [hook-techniques.md](../guides/hook-techniques.md)

## 字数标准
| 体量 | 每章字数 | 总字数 | 初始化命令 |
|------|---------|-------|-----------|
| 短篇 | 2000-4000 | 2万-4万 | `--type short` |
| 中篇 | 3000-5000 | 9万-15万 | `--type medium`（默认） |
| 长篇 | 3000-5000 | 18万-50万+ | `--type long` |
| 番茄连载 | 2000-3000（分阶段） | 10万-100万+ | `--type tomato` |

番茄连载分阶段字数门禁由 `state.json` 中 `project.writing_type` 字段控制，`quality_gate.py` 自动读取并应用。

## 禁用/慎用词表
禁用于正文（来源于多个项目的去AI味实践）：

**高频AI词**：不禁、仿佛、映入眼帘、心中暗道、沉声道、嘴角微扬

**弱副词**：微微、淡淡、缓缓、轻轻、悄然

**套话**：未来可期、前途无量、空气仿佛凝固、气氛微妙

**论文腔**：不难看出、由此可见、值得注意的是

## 质量门禁脚本
```bash
python3 scripts/quality_gate.py check              # 检查最新一章
python3 scripts/quality_gate.py check --chapter 5  # 指定章节
python3 scripts/quality_gate.py report              # 全部章节报告
```

## 事件矩阵脚本
```bash
python3 scripts/event_matrix.py check     # 检查冷却状态
python3 scripts/event_matrix.py rhythm    # 节奏健康度
python3 scripts/event_matrix.py suggest   # 推荐下章事件类型
python3 scripts/event_matrix.py add --type conflict_thrill --desc "冲突描述"
```

## AI味检测脚本
```bash
python3 scripts/anti_ai_detector.py detect manuscript/第001章-xxx.md
python3 scripts/anti_ai_detector.py report manuscript/第001章-xxx.md
python3 scripts/anti_ai_detector.py polish manuscript/第001章-xxx.md
```

## 语料检索脚本
```bash
python3 scripts/search_corpus.py list-tags
python3 scripts/search_corpus.py search-type --type "开头钩子" --tag "危机压身"
python3 scripts/search_corpus.py search-keyword --keyword "穿越" --limit 5
```

## 知识图谱脚本
```bash
python3 scripts/story_graph.py add-node --id char_01 --type character --name "主角"
python3 scripts/story_graph.py add-edge --source char_01 --target char_02 --type ally
python3 scripts/story_graph.py related --id char_01
python3 scripts/story_graph.py foreshadowing --status open
