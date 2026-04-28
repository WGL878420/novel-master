# Phase 0: 初始化

## 目标
加载用户偏好、检测未完成项目、展示当前状态。

## 执行流程

### 1. 加载用户偏好
- 读取 `~/.claude/skills/china-novelist/user-preferences.json`
- 如不存在则使用默认值

### 2. 检测未完成项目
- 扫描 `./chinese-novelist/` 目录下的项目文件夹
- 检测方式：检查是否存在 `state/current/state.json` 且 `progress.status != "complete"`
- 如检测到未完成项目，询问用户是否续写

### 3. 显示状态
- 新项目：显示写作模式选择提示
- 续写项目：显示当前进度（已完成 X/Y 章）、上次中断位置

## 输出
- 已加载的偏好（题材偏好、常用风格、默认章节数）
- 续写项目信息（如有）
- 确认进入 Phase 1

## 参考
- 来自：PenglongHuang/chinese-novelist-skill 的 Phase 0
