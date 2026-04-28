# Phase 4: 知识库初始化

## 目标
在正式写作前，创建完整的一致性保障体系。

## 执行流程

### 1. 创建 bible/（永久不变）
使用 `templates/bible/` 中的模板创建：

| 文件 | 内容 | 来源 |
|------|------|------|
| `00-world-building.md` | 世界观设定、阵营、地理、力量体系 | 来自 Phase 2 Q&A |
| `01-character-profiles.md` | 从 Phase 3 完善的人物档案 | 来自 Phase 3 |
| `02-style-guide.md` | 文体风格指南、禁用词表、去AI味要求 | 模板+自定义 |
| `03-outline.md` | 完整大纲 | 来自 Phase 3 |
| `04-research.md` | 参考资料、考据笔记 | 可选 |

**bible 原则**：一旦创建，写作过程中永不修改。修改 bible 需要通过 `/改纲续写` 流程。

### 2. 初始化 state/
```json
{
  "project": { "name": "xxx", "genre": "xxx", "total_chapters": 30 },
  "progress": { "current_chapter": 0, "completed_chapters": [], "status": "ready" },
  "summary": {
    "latest_events": [],
    "pending_foreshadowing": [],
    "active_conflicts": []
  }
}
```

### 3. 初始化知识图谱
使用 `scripts/story_graph.py` 添加主要节点：
```bash
python3 scripts/story_graph.py add-node --id protagonist --type character --name "主角名"
python3 scripts/story_graph.py add-node --id main_antagonist --type character --name "反派名"
python3 scripts/story_graph.py add-edge --source protagonist --target main_antagonist --type enemy
```

### 4. 初始化事件矩阵
使用 `scripts/event_matrix.py` 确认默认冷却配置。

### 5. 初始化时间线
创建 `knowledge/timeline.md`，记录第0天的初始状态。

## 输出
- bible/ 完整目录（5个文件）
- state/ 已初始化
- 知识图谱已建立
- 准备进入 Phase 5

## 参考
来自：Claude-Book 的 bible/state 分离 + leenbj 的知识图谱
