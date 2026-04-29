# 起点小说发布功能

## What This Is

为 novel-master 添加起点小说自动发布功能：通过 Playwright 浏览器自动化，实现登录验证后指定章节上传到起点作家后台草稿箱。

## Core Value

用户可以在写作工作流中直接上传章节到起点，无需手动复制粘贴。

## Requirements

### Active

- [ ] 起点登录功能（手机验证码）
- [ ] 指定章节上传到草稿箱
- [ ] 状态查询（查看已上传章节）
- [ ] 与现有番茄发布功能共用状态管理框架

### Out of Scope

- 创建新书功能（书籍已在起点创建好）
- 批量上传功能
- 自动发布（直接发布而非草稿箱）

## Context

novel-master 已实现番茄小说自动发布（`fanqie_publish.py`），使用 Playwright 浏览器自动化方案：
- 通过页面 fetch 调用番茄 API
- 认证状态持久化到 `~/.novel-master/fanqie-auth-state.json`
- 上传状态记录在 `state/fanqie-publish-state.json`

起点发布采用相同技术方案，参考：
- `scripts/fanqie_publish.py` — 完整实现（650+ 行）
- `.planning/codebase/ARCHITECTURE.md` — 发布流程架构

**已知起点信息：**
- 作家后台：https://write.qq.com
- 书籍 CBID：35730802204107809
- 新建章节草稿页面示例：https://write.qq.com/portal/booknovels/chaptertmp/CBID/35730802204107809/addType/1.html
- 登录方式：手机验证码（不支持账号密码）

## Constraints

- **技术限制**：依赖 Playwright 浏览器自动化，需安装 chromium
- **登录方式**：仅支持手机验证码（起点不支持账密登录）
- **上传方式**：浏览器表单上传，不依赖固定 API 接口
- **认证状态**：复用 `~/.novel-master/` 目录存储认证状态

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Playwright 方案而非 API | 番茄验证可行，起点页面结构未知但可探索 | — Pending |
| 复用现有认证状态文件结构 | 保持一致性，qidian-auth-state.json | — Pending |
| 不批量上传 | 用户明确指定章节 | — Pending |
| 草稿箱而非直接发布 | 草稿箱更安全，给用户检查机会 | — Pending |

---
*Last updated: 2026/04/29 after initialization*
