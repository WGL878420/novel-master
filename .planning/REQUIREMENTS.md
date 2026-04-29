# Requirements: 起点小说发布功能

**Defined:** 2026-04-29
**Core Value:** 用户可以在写作工作流中直接上传章节到起点，无需手动复制粘贴

## v1 Requirements

### 起点发布

- [ ] **QD-01**: 用户可以通过 `qidian_publish.py login` 命令登录起点作家后台（手机验证码）
- [ ] **QD-02**: 用户可以通过 `qidian_publish.py upload -p <项目> --chapter N` 上传指定章节到草稿箱
- [ ] **QD-03**: 用户可以通过 `qidian_publish.py status -p <项目>` 查看已上传章节列表
- [ ] **QD-04**: 认证状态持久化到 `~/.novel-master/qidian-auth-state.json`
- [ ] **QD-05**: 发布状态记录在 `state/qidian-publish-state.json`

## Out of Scope

| Feature | Reason |
|---------|--------|
| 创建新书 | 书籍已在起点创建好 |
| 批量上传 | 用户明确指定单章上传 |
| 直接发布 | 仅上传到草稿箱，用户自行检查后发布 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| QD-01 | Phase 1 | ✓ Complete |
| QD-02 | Phase 1 | ✓ Complete |
| QD-03 | Phase 1 | ✓ Complete |
| QD-04 | Phase 1 | ✓ Complete |
| QD-05 | Phase 1 | ✓ Complete |

**Coverage:**
- v1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-29*
*Last updated: 2026-04-29 after initial definition*
