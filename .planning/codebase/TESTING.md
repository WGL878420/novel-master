# Testing Patterns — Novel Master

## Overview

This codebase uses **CLI-driven validation** rather than a formal test framework. There are no `pytest` or `unittest` imports. Quality assurance is achieved through:

1. **Quality gate checks** — per-chapter validation scripts
2. **Continuity checks** — cross-chapter consistency
3. **Manual CLI testing** — human-run commands
4. **State file verification** — JSON state as correctness witness

---

## 1. Quality Gate System

`quality_gate.py` implements a **five-step gate** that each chapter must pass:

```bash
python3 scripts/quality_gate.py check -p <project>
```

### The Five Checks

| Check | Function | Pass Criteria |
|-------|----------|---------------|
| 字数检查 | `check_word_count()` | 3000-3500 Chinese chars |
| 开头抓力 | `check_opening_grab()` | Score >= 2/3 (dialogue/action/conflict) |
| 章末钩子 | `check_hook()` | Score >= 2/4 (question/twist/action-break) |
| AI味检测 | `check_ai_indicators()` | Density < 3/千字 |
| 冲突检测 | `check_conflict()` | >= 3 conflict-word occurrences |

### Result Structure

```python
result = {
    "chapter": 5,
    "file": ".../manuscript/第005章-xxx.md",
    "timestamp": "2026-04-29T10:00:00.000000",
    "overall": "pass",        # or "fail", "conditional_pass"
    "checks": {
        "word_count": {"status": "pass", "count": 3200, "min": 3000, "max": 3500, ...},
        "opening": {"status": "pass", "score": 2, ...},
        "hook": {"status": "pass", "score": 3, ...},
        "ai_indicators": {"status": "pass", "density": 1.5, ...},
        "conflict": {"status": "pass", "found": 5, ...},
    },
    "summary": {
        "total_checks": 5,
        "passed": 5,
        "warnings": 0,
        "failed": 0,
    },
}
```

### Gate Record Files

Passed gates are saved to `gates/第NNN章-gate.json` for audit trail. The iron rule (字数铁律) violations do **not** save records — chapter must be rewritten.

### Exit Code Behavior

```python
# Non-zero exit on failure
if result["overall"] == "fail" or result["checks"]["word_count"].get("iron_rule"):
    import sys
    sys.exit(1)
```

---

## 2. Continuity Checking

`story_graph.py` provides `check-continuity` for cross-chapter consistency:

```bash
python3 scripts/story_graph.py -p <project> check-continuity
```

### Three Continuity Checks

```python
def check_continuity(project_root: Path) -> List[str]:
    # 1. Basic consistency (dangling edges)
    issues.extend(check_consistency(project_root))

    # 2. Attribute contradictions
    #    Same key, different value at different chapters
    for n in graph["nodes"]:
        for attr in attrs:
            if key in seen and seen[key]["value"] != attr["value"]:
                issues.append(f"属性矛盾 [{n['name']}.{key}]: ...")

    # 3. Stale foreshadowing
    #    Foreshadowing introduced >25 chapters ago and still "open"
    if n["type"] == "foreshadowing" and (latest_ch - intro_ch) >= 25:
        issues.append(f"伏笔长期未解 ...")
```

---

## 3. Bible Completeness Check

```bash
python3 scripts/story_graph.py -p <project> check-bible
```

Validates that bible files have no unfilled `（待定）` placeholders:

```python
# Regex patterns matched:
re.match(r"^[-*]\s+\*{0,2}\S+\*{0,2}：$", stripped)   # empty after label
re.match(r"^[-*]\s+\*{0,2}\S+\*{0,2}：\S", stripped)  # filled
"（待定）" in stripped                                  # placeholder
```

Reports percentage filled per file.

---

## 4. Rhythm Checking

`event_matrix.py` validates story pacing:

```bash
python3 scripts/event_matrix.py rhythm -p <project>
```

### Rules

- Every 5 chapters must contain at least 1 `bond_deepening` or `world_painting` event
- Event types have cooldowns (same type cannot appear too frequently)

```python
DEFAULT_COOLDOWNS = {
    "conflict_thrill": 2,
    "bond_deepening": 1,
    "faction_building": 2,
    "world_painting": 3,
    "tension_escalation": 2,
}
```

---

## 5. AI-Flavor Detection

`anti_ai_detector.py` scans for 11 AI-pattern categories:

```bash
python3 scripts/anti_ai_detector.py report <chapter-file>
```

### Categories (11 total)

| Category | Weight | Examples |
|----------|--------|---------|
| 高频AI词汇 | 2 | 不禁、仿佛、映入眼帘 |
| 弱副词滥用 | 1 | 微微、淡淡、缓缓 |
| 意义膨胀 | 2 | 前所未有、里程碑 |
| 套话结语 | 2 | 未来可期、前途无量 |
| 论文腔开头 | 1 | 不难看出、由此可见 |
| 书面腔 | 1 | 于是乎、与此同时 |
| 三重排比 | 2 | (regex: `([^，！？\n]{2,10}，){3}`) |
| 情绪解释过多 | 2 | 她感到、他内心 |
| AI 常用句式 | 1 | 仿佛凝固、空气安静 |
| 过度修饰 | 1 | 清冷、深邃、邪魅 |
| 一问一答式对话 | 2 | 什么情况、怎么死的 |
| 完美逻辑链 | 2 | 首先...其次...最后 |
| 信息堆砌 | 2 | 通话记录、社交网络 |
| 推理结论直给 | 1 | 这说明、由此可见 |

### Quality Levels

| Density (/千字) | Level | Verdict |
|-----------------|-------|---------|
| <= 1 | 优秀 | pass |
| <= 3 | 良好 | pass |
| <= 6 | 需优化 | warn |
| > 6 | AI味重 | fail |

---

## 6. Manual Testing Workflows

### New Project

```bash
python3 scripts/init_project.py "书名" -g 悬疑 -c 20
cd <generated-project>
python3 scripts/quality_gate.py check -p .
python3 scripts/story_graph.py -p . brief --chapter 1
```

### Writing Cycle

```bash
# Before writing
python3 scripts/story_graph.py -p . brief --chapter N
python3 scripts/story_graph.py -p . check-continuity

# After writing
python3 scripts/quality_gate.py check -p . --chapter N
python3 scripts/story_graph.py -p . post-write --chapter N

# Periodic checks
python3 scripts/story_graph.py -p . check-bible
python3 scripts/story_graph.py -p . sync-status
```

### Publishing

```bash
python3 scripts/fanqie_publish.py upload -p . --chapter N
```

---

## 7. State Files as Verification

State files in `state/current/` serve as correctness witnesses:

```json
{
  "progress": {
    "current_chapter": 5,
    "completed_chapters": [1, 2, 3, 4, 5],
    "synced_up_to_chapter": 5
  },
  "summary": {
    "latest_events": ["第5章摘要..."],
    "active_conflicts": [],
    "pending_foreshadowing": []
  }
}
```

`synced_up_to_chapter` tracks whether `post-write` has been run. `brief` warns if chapters exist without sync.

---

## 8. No Formal Test Files

This codebase has **no test files** (`test_*.py`, `*_test.py`, `tests/` directory). Validation is entirely CLI-driven and human-executed. The quality gate system is the closest equivalent to automated testing.

---

## 9. Testing Anti-Patterns to Avoid

- **Do not** add `pytest` or `unittest` — the existing workflow is CLI-based
- **Do not** modify gate logic arbitrarily — iron rules enforce writing discipline
- **Do not** skip `post-write` — sync tracking depends on it
