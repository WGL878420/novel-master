#!/usr/bin/env python3
"""Novel Master: 知识图谱管理 - 人物/事件/伏笔关系维护"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils import ensure_dir, read_json, write_json, read_md, write_md, get_chapter_files, count_chinese_chars

NODE_TYPES = {
    "character": "人物",
    "location": "地点",
    "faction": "势力",
    "item": "物品",
    "event": "事件",
    "foreshadowing": "伏笔",
    "world_rule": "世界规则",
    "power_system": "力量体系",
}

EDGE_TYPES = {
    "ally": "盟友",
    "enemy": "敌对",
    "mentor": "师徒",
    "subordinate": "从属",
    "emotional": "感情",
    "belongs_to": "属于",
    "located_at": "位于",
    "triggers": "触发",
    "foreshadows": "预示",
    "possesses": "拥有",
    "related_to": "关联",
}


def load_graph(project_root: Path) -> dict:
    path = project_root / "knowledge" / "story_graph.json"
    if path.exists():
        return read_json(path)
    return {"nodes": [], "edges": [], "version": 1, "last_updated": datetime.now().isoformat()}


def save_graph(project_root: Path, graph: dict):
    graph["version"] = graph.get("version", 1) + 1
    graph["last_updated"] = datetime.now().isoformat()
    ensure_dir(project_root / "knowledge")
    write_json(project_root / "knowledge" / "story_graph.json", graph)


def add_node(project_root: Path, node_id: str, node_type: str, name: str, properties: Optional[Dict] = None, chapter_intro: Optional[int] = None):
    """添加节点"""
    graph = load_graph(project_root)

    # 检查是否已存在
    for n in graph["nodes"]:
        if n["id"] == node_id:
            print(f"  ℹ️  节点已存在: {name}")
            return

    node = {
        "id": node_id,
        "type": node_type,
        "name": name,
        "properties": properties or {},
        "created_at": datetime.now().isoformat(),
        "chapter_intro": chapter_intro,
    }
    graph["nodes"].append(node)
    save_graph(project_root, graph)
    type_label = NODE_TYPES.get(node_type, node_type)
    print(f"  ✅ 添加节点 [{type_label}] {name}")


def add_edge(project_root: Path, source: str, target: str, edge_type: str, properties: Optional[Dict] = None):
    """添加关系边"""
    graph = load_graph(project_root)
    edge = {
        "source": source,
        "target": target,
        "type": edge_type,
        "properties": properties or {},
        "created_at": datetime.now().isoformat(),
    }
    graph["edges"].append(edge)
    save_graph(project_root, graph)
    type_label = EDGE_TYPES.get(edge_type, edge_type)
    print(f"  ✅ 添加关系 [{type_label}] {source} -> {target}")


def add_attr(project_root: Path, node_id: str, key: str, value: str, chapter: int):
    """为节点添加带章节标记的属性（追踪人物外貌、位置、状态等随章节的变化）"""
    graph = load_graph(project_root)
    node = get_node(graph, node_id)
    if not node:
        print(f"  ❌ 节点未找到: {node_id}")
        return

    if "attributes" not in node:
        node["attributes"] = []

    # 检查与前文是否矛盾
    for attr in node["attributes"]:
        if attr["key"] == key and attr["value"] != value:
            print(f"  ⚠️  与前文矛盾！第{attr['chapter']}章记录为「{attr['value']}」，现改为「{value}」")

    node["attributes"].append({
        "key": key,
        "value": value,
        "chapter": chapter,
        "timestamp": datetime.now().isoformat(),
    })
    save_graph(project_root, graph)
    print(f"  ✅ 记录属性 [{node_id}.{key} = {value}] (第{chapter}章)")


def get_node(graph: dict, node_id: str) -> Optional[dict]:
    for n in graph["nodes"]:
        if n["id"] == node_id:
            return n
    return None


def get_related(project_root: Path, node_id: str, max_depth: int = 1) -> Dict:
    """获取与节点相关的所有节点和边"""
    graph = load_graph(project_root)

    related_nodes = set()
    related_edges = []

    for e in graph["edges"]:
        if e["source"] == node_id or e["target"] == node_id:
            related_edges.append(e)
            related_nodes.add(e["source"])
            related_nodes.add(e["target"])

    return {
        "center": get_node(graph, node_id),
        "related_nodes": [get_node(graph, nid) for nid in related_nodes if nid != node_id and get_node(graph, nid)],
        "edges": related_edges,
    }


def check_consistency(project_root: Path) -> List[str]:
    """检查图谱一致性"""
    graph = load_graph(project_root)
    issues = []
    node_ids = {n["id"] for n in graph["nodes"]}

    for e in graph["edges"]:
        if e["source"] not in node_ids:
            issues.append(f"边引用不存在的source节点: {e['source']}")
        if e["target"] not in node_ids:
            issues.append(f"边引用不存在的target节点: {e['target']}")

    return issues


def check_continuity(project_root: Path) -> List[str]:
    """全面连续性检查：属性矛盾 + 伏笔超期 + 悬空边"""
    issues = []

    # 1. 基本一致性（悬空边）
    issues.extend(check_consistency(project_root))

    # 2. 属性矛盾
    graph = load_graph(project_root)
    for n in graph["nodes"]:
        attrs = n.get("attributes", [])
        seen = {}
        for attr in attrs:
            key = attr["key"]
            if key in seen and seen[key]["value"] != attr["value"]:
                issues.append(
                    f"  属性矛盾 [{n['name']}.{key}]: "
                    f"第{seen[key]['chapter']}章 = 「{seen[key]['value']}」 ≠ "
                    f"第{attr['chapter']}章 = 「{attr['value']}」"
                )
            seen[key] = attr

    # 3. 伏笔长期未解
    latest_ch = 0
    for n in graph["nodes"]:
        intro = n.get("chapter_intro")
        if intro and intro > latest_ch:
            latest_ch = intro
    # 也从已完成章节获取
    state_file = project_root / "state" / "current" / "state.json"
    if state_file.exists():
        try:
            state = read_json(state_file)
            completed = state.get("progress", {}).get("completed_chapters", [])
            if completed:
                latest_ch = max(latest_ch, max(completed))
        except Exception:
            pass

    for n in graph["nodes"]:
        if n["type"] == "foreshadowing":
            status = n.get("properties", {}).get("status", "open")
            intro_ch = n.get("chapter_intro")
            if status == "open" and intro_ch and (latest_ch - intro_ch) >= 25:
                issues.append(
                    f"  伏笔长期未解 [{n['id']}]: "
                    f"第{intro_ch}章引入，已过{latest_ch - intro_ch}章"
                )

    return issues


def generate_brief(project_root: Path, chapter: int) -> str:
    """生成写作简报：汇集进度、图谱、事件矩阵、伏笔，确保写前掌握全局"""
    state_file = project_root / "state" / "current" / "state.json"
    state = read_json(state_file) if state_file.exists() else {}
    graph = load_graph(project_root)

    matrix_file = project_root / "knowledge" / "event_matrix.json"
    matrix = read_json(matrix_file) if matrix_file.exists() else {}

    lines = []
    lines.append(f"# 写作简报 — 第{chapter}章\n")

    # ── 项目状态 ──
    proj = state.get("project", {})
    lines.append("## 项目状态")
    lines.append(f"- 小说：{proj.get('name', '未知')}")
    lines.append(f"- 题材：{proj.get('genre', '未知')}")
    estimate = proj.get("estimated_chapters")
    if estimate:
        lines.append(f"- 进度：第{chapter}章（初始规划约{estimate}章，不设上限）")
    else:
        lines.append(f"- 进度：第{chapter}章（不设上限）")
    current = state.get("progress", {}).get("current_chapter", 0)
    if current:
        lines.append(f"- 上一章完成：第{current}章")

    # 检查大纲剩余量
    outline_file = project_root / "bible" / "03-outline.md"
    if outline_file.exists():
        try:
            ot = read_md(outline_file)
            last_outline_ch = 0
            for line in ot.split("\n"):
                if line.startswith("|") and len(line.split("|")) >= 2:
                    try:
                        ch = int(line.split("|")[1].strip())
                        if ch > last_outline_ch:
                            last_outline_ch = ch
                    except ValueError:
                        pass
            remaining = last_outline_ch - chapter
            if remaining <= 0:
                lines.append(f"- ⚠️ **章纲已用完！** 立即执行 extend-outline 扩展大纲")
            elif remaining <= 3:
                lines.append(f"- ⚠️ **章纲仅剩 {remaining} 章**，写完前记得 extend-outline")
        except Exception:
            pass

    # 检查同步状态
    synced_to = state.get("progress", {}).get("synced_up_to_chapter", 0)
    completed = state.get("progress", {}).get("completed_chapters", [])
    if completed:
        max_completed = max(completed)
        unsynced = [c for c in completed if c > synced_to]
        if synced_to < 1 and len(completed) >= 1:
            lines.append(f"- ⚠️ **前 {len(completed)} 章未同步！** 立即运行 post-write")
        elif unsynced:
            lines.append(f"- ⚠️ **{len(unsynced)} 章未同步**（第{unsynced[0]}-{unsynced[-1]}章），运行 post-write 更新")
        elif synced_to > 0:
            lines.append(f"- ✅ 已同步到第{synced_to}章")

    lines.append("")

    # ── 本章章纲 ──
    if outline_file.exists():
        try:
            ot = read_md(outline_file)
            for line in ot.split("\n"):
                if line.startswith("|") and len(line.split("|")) >= 2:
                    try:
                        ch = int(line.split("|")[1].strip())
                        if ch == chapter:
                            parts = [p.strip() for p in line.split("|")]
                            lines.append("## 本章章纲")
                            col_names = ["章号", "章名", "主线", "副线/冲突", "新信息", "钩子"]
                            for idx, col in enumerate(col_names):
                                if idx < len(parts) and parts[idx]:
                                    lines.append(f"- **{col}**: {parts[idx]}")
                            lines.append("")
                            break
                    except ValueError:
                        pass
        except Exception:
            pass

    # ── 最近事件回顾（合并 timeline + state） ──
    events = state.get("summary", {}).get("latest_events", [])
    timeline_file = project_root / "knowledge" / "timeline.md"
    timeline_events = []
    if timeline_file.exists():
        try:
            tl = read_md(timeline_file)
            for line in reversed(tl.split("\n")):
                if line.startswith("- 第") and "章" in line:
                    timeline_events.append(line.lstrip("- ").strip())
                    if len(timeline_events) >= 3:
                        break
        except Exception:
            pass

    merged_events = []
    seen = set()
    for ev in (timeline_events + events):
        if ev and ev not in seen:
            merged_events.append(ev)
            seen.add(ev)
        if len(merged_events) >= 5:
            break

    if merged_events:
        lines.append("## 最近事件回顾")
        for i, ev in enumerate(merged_events[:5], 1):
            lines.append(f"{i}. {ev}")
        lines.append("")

    # ── 活跃冲突 ──
    conflicts = state.get("summary", {}).get("active_conflicts", [])
    if conflicts:
        lines.append("## 活跃冲突")
        for c in conflicts:
            lines.append(f"- {c}")
        lines.append("")

    # ── 待解伏笔 ──
    fs_list = [
        n for n in graph.get("nodes", [])
        if n["type"] == "foreshadowing"
        and n.get("properties", {}).get("status", "open") == "open"
    ]
    if fs_list:
        lines.append(f"## 待解伏笔 ({len(fs_list)})")
        for fs in fs_list:
            desc = fs.get("properties", {}).get("description", fs["id"])
            intro = fs.get("chapter_intro")
            ch_tag = f" [第{intro}章引入]" if intro else ""
            lines.append(f"- {desc}{ch_tag}")
        lines.append("")

    # ── 活跃角色（优先显示最近登场的） ──
    chars = [n for n in graph.get("nodes", []) if n["type"] == "character"]
    if chars:
        def _recent_score(c):
            intro = c.get("chapter_intro", 0) or 0
            attrs = c.get("attributes", [])
            last_attr_ch = max((a.get("chapter", 0) for a in attrs), default=0)
            return max(intro, last_attr_ch)

        chars_sorted = sorted(chars, key=_recent_score, reverse=True)
        recent_chars = chars_sorted[:10]
        lines.append(f"## 活跃角色 ({len(recent_chars)}/{len(chars)} 显示最近)")
        for c in recent_chars:
            name = c["name"]
            attrs = c.get("attributes", [])
            latest = {}
            for a in attrs:
                latest[a["key"]] = a["value"]
            attr_str = " | ".join(f"{k}={v}" for k, v in latest.items())
            intro_tag = f" [第{c.get('chapter_intro', '?')}章]" if c.get("chapter_intro") else ""
            if attr_str:
                lines.append(f"- **{name}**{intro_tag}: {attr_str}")
            else:
                lines.append(f"- **{name}**{intro_tag}")
        lines.append("")

    # ── 地点 ──
    locs = [n for n in graph.get("nodes", []) if n["type"] == "location"]
    if locs:
        lines.append("## 地点")
        for loc in locs:
            loc_attrs = loc.get("attributes", [])
            latest = {}
            for a in loc_attrs:
                latest[a["key"]] = a["value"]
            detail = f" — {latest.get('场景', '')}" if "场景" in latest else ""
            lines.append(f"- {loc['name']}{detail}")
        lines.append("")

    # ── 节奏建议 ──
    try:
        from event_matrix import suggest_next_event, check_rhythm, EVENT_TYPES
        suggestion = suggest_next_event(project_root, chapter)
        rhythm = check_rhythm(project_root)
        lines.append("## 节奏建议")
        lines.append(f"- 推荐事件类型：{EVENT_TYPES.get(suggestion, suggestion)}")
        if rhythm.get("warnings"):
            for w in rhythm["warnings"]:
                lines.append(f"- ⚠️ {w}")
        lines.append("")
    except Exception:
        pass

    return "\n".join(lines)


def _extract_character_names(project_root: Path) -> List[str]:
    """从 bible/01-character-profiles.md 提取已定义的角色名"""
    profile_file = project_root / "bible" / "01-character-profiles.md"
    if not profile_file.exists():
        return []
    text = read_md(profile_file)
    names = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## ") or line.startswith("### "):
            name = line.lstrip("#").strip()
            name = re.sub(r'[（(].*?[）)]', '', name).strip()
            if name and len(name) <= 10:
                names.append(name)
        m = re.match(r'^[-*]\s+\*{0,2}姓名\*{0,2}[：:]\s*(.+)', line)
        if m:
            n = m.group(1).strip()
            if n and n not in names:
                names.append(n)
    return names


def _extract_location_names(project_root: Path) -> List[str]:
    """从 bible/00-world-building.md 提取已定义的地点名"""
    wb_file = project_root / "bible" / "00-world-building.md"
    if not wb_file.exists():
        return []
    text = read_md(wb_file)
    locs = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## ") or line.startswith("### "):
            name = line.lstrip("#").strip()
            name = re.sub(r'[（(].*?[）)]', '', name).strip()
            if name and len(name) <= 15 and any(k in line.lower() for k in ["地点", "地图", "场景", "城", "山", "宗", "国", "域", "镇", "村", "岛", "谷", "洞", "殿", "阁", "楼", "府"]):
                locs.append(name)
    return locs


def _auto_sync_graph(project_root: Path, chapter: int, text: str):
    """自动将正文中出现的 bible 角色/地点写入知识图谱（首次出现才添加）"""
    if not text:
        return [], []

    graph = load_graph(project_root)
    existing_ids = {n["id"] for n in graph["nodes"]}
    existing_names = {n["name"] for n in graph["nodes"]}

    added_chars = []
    added_locs = []

    char_names = _extract_character_names(project_root)
    for name in char_names:
        if name in text and name not in existing_names:
            node_id = name.lower().replace(" ", "_")
            if node_id not in existing_ids:
                add_node(project_root, node_id, "character", name, chapter_intro=chapter)
                added_chars.append(name)
                existing_ids.add(node_id)
                existing_names.add(name)

    loc_names = _extract_location_names(project_root)
    for name in loc_names:
        if name in text and name not in existing_names:
            node_id = f"loc_{name.lower().replace(' ', '_')}"
            if node_id not in existing_ids:
                add_node(project_root, node_id, "location", name, chapter_intro=chapter)
                added_locs.append(name)
                existing_ids.add(node_id)
                existing_names.add(name)

    return added_chars, added_locs


EVENT_TYPE_KEYWORDS = {
    "bond_deepening": [
        "信任", "温柔", "拥抱", "泪", "思念", "关心", "喜欢", "爱", "心疼",
        "道歉", "原谅", "陪伴", "依赖", "情感", "暧昧", "告白", "心意",
        "默契", "守护", "承诺", "表白", "亲吻", "深情",
    ],
    "world_painting": [
        "地图", "历史", "规则", "体系", "阵法", "丹药", "功法", "秘境",
        "传说", "遗迹", "文明", "种族", "大陆", "王国", "势力范围",
        "修炼", "境界", "法则", "天地", "灵气",
    ],
    "faction_building": [
        "势力", "联盟", "门派", "组织", "招募", "收编", "盟友", "投靠",
        "效忠", "反叛", "阵营", "帮派", "家族", "宗门", "弟子",
    ],
    "tension_escalation": [
        "升级", "突破", "晋级", "新敌", "阴谋", "更强", "觉醒",
        "进化", "蜕变", "瓶颈", "顿悟", "成长", "实力",
    ],
    "conflict_thrill": [
        "冲突", "战斗", "对决", "争吵", "背叛", "追杀", "逃亡",
        "生死", "危机", "对抗", "打斗", "愤怒", "复仇", "陷阱",
    ],
}


def _classify_event_type(text: str) -> str:
    """根据正文内容自动推断事件类型"""
    scores = {}
    for etype, keywords in EVENT_TYPE_KEYWORDS.items():
        score = sum(text.count(kw) for kw in keywords)
        scores[etype] = score

    if not scores or max(scores.values()) == 0:
        return "conflict_thrill"

    return max(scores, key=scores.get)


def post_write(project_root: Path, chapter: int):
    """写后更新：自动同步知识图谱 + 智能分类事件 + 更新 timeline"""
    if chapter < 1:
        print("❌ 无效章节号")
        return

    # 1. 读取本章文件和 state
    state_file = project_root / "state" / "current" / "state.json"
    state = read_json(state_file) if state_file.exists() else {}

    matches = sorted(project_root.glob(f"manuscript/第{chapter:03d}章-*.md"))
    if not matches:
        print(f"  ⚠️  未找到第{chapter}章手稿，跳过正文分析")
        text = ""
    else:
        text = read_md(matches[0])

    # 2. 自动同步知识图谱（从 bible 提取角色/地点，匹配正文后写入图谱）
    added_chars, added_locs = _auto_sync_graph(project_root, chapter, text)

    # 3. 更新 timeline.md
    timeline_file = project_root / "knowledge" / "timeline.md"
    ensure_dir(timeline_file.parent)
    if not timeline_file.exists():
        write_md(timeline_file, "# 时间线\n\n")
    evts = state.get("summary", {}).get("latest_events", [])
    summary = evts[0] if evts else "（章节已记录）"
    with open(timeline_file, "a", encoding="utf-8") as f:
        f.write(f"- 第{chapter}章: {summary}\n")

    # 4. 同步更新 event_matrix（智能分类事件类型）
    matrix_file = project_root / "knowledge" / "event_matrix.json"
    event_type = _classify_event_type(text) if text else "conflict_thrill"
    if matrix_file.exists():
        matrix = read_json(matrix_file)
        already_logged = any(e["chapter"] == chapter for e in matrix.get("events", []))
        if not already_logged:
            matrix.setdefault("events", []).append({
                "chapter": chapter,
                "type": event_type,
                "description": summary[:100],
                "timestamp": datetime.now().isoformat(),
            })
            write_json(matrix_file, matrix)

    # 5. 标记 synced_up_to_chapter
    old_sync = state.get("progress", {}).get("synced_up_to_chapter", 0)
    state.setdefault("progress", {})["synced_up_to_chapter"] = chapter
    state["last_updated"] = datetime.now().isoformat()
    ensure_dir(state_file.parent)
    write_json(state_file, state)

    # 6. 扫描正文，匹配知识图谱中的已有角色/地点
    graph = load_graph(project_root)
    chars_in_text = [n["name"] for n in graph.get("nodes", [])
                     if n["type"] == "character" and text and n["name"] in text]
    locs_in_text = [n["name"] for n in graph.get("nodes", [])
                    if n["type"] == "location" and text and n["name"] in text]

    try:
        from event_matrix import EVENT_TYPES
        event_label = EVENT_TYPES.get(event_type, event_type)
    except ImportError:
        event_label = event_type

    print(f"  ✅ 同步标记：第{chapter}章（之前同步到第{old_sync}章）")
    print(f"  ✅ 时间线已更新")
    print(f"  ✅ 事件矩阵已同步（类型：{event_label}）")
    if added_chars:
        print(f"  🆕 自动添加角色到图谱：{', '.join(added_chars)}")
    if added_locs:
        print(f"  🆕 自动添加地点到图谱：{', '.join(added_locs)}")
    if chars_in_text:
        print(f"  📖 本章出现的角色：{', '.join(chars_in_text)}")
    if locs_in_text:
        print(f"  📖 本章出现的地点：{', '.join(locs_in_text)}")
    print()
    print(f"  {'='*50}")
    print(f"  写后检查清单（图谱已自动同步，以下仅需人工确认）")
    print(f"  {'='*50}")
    print(f"  1. 角色属性变化？→ add-attr（如身份/位置/状态变更）")
    print(f"  2. 角色关系变化？→ add-edge（如新结盟/敌对/感情）")
    print(f"  3. 伏笔")
    print(f"     - 埋新伏笔？→ add-node --type foreshadowing --chapter {chapter}")
    print(f"     - 收伏笔？→ resolve-fs --id xxx")
    print(f"  4. 下一步")
    print(f"     - brief 看节奏建议")
    print(f"     - 大纲快用完则 extend-outline")
    print(f"  {'='*50}")


def check_bible(project_root: Path) -> dict:
    """检查 bible 文件的填写完整度，返回空字段数"""
    bible_dir = project_root / "bible"
    if not bible_dir.exists():
        print("❌ 未找到 bible 目录")
        return {}

    files = {
        "00-world-building.md": "世界观",
        "01-character-profiles.md": "角色档案",
        "02-style-guide.md": "风格指南",
        "03-outline.md": "大纲",
        "04-research.md": "研究资料",
    }

    total_empty = 0
    total_fields = 0
    results = {}

    for fname, label in files.items():
        fpath = bible_dir / fname
        if not fpath.exists():
            results[fname] = {"status": "missing", "empty": 0, "total": 0}
            continue

        text = read_md(fpath)
        lines = text.split("\n")
        empty_after_label = 0
        field_count = 0

        for line in lines:
            stripped = line.strip()
            # 匹配 " - **xxx**：" 或 "- xxx：" 格式（冒号结尾无内容）
            if re.match(r"^[-*]\s+\*{0,2}\S+\*{0,2}：$", stripped):
                empty_after_label += 1
                field_count += 1
            elif re.match(r"^[-*]\s+\*{0,2}\S+\*{0,2}：\S", stripped):
                field_count += 1
            # 匹配（待定）占位符
            if "（待定）" in stripped or re.match(r".*\{.+\}.*", stripped):
                empty_after_label += 1
                field_count += 1

        total_empty += empty_after_label
        total_fields += field_count
        pct = 100 if field_count == 0 else round((field_count - empty_after_label) / field_count * 100)
        results[fname] = {"status": "ok", "filled_pct": pct, "empty": empty_after_label, "total": field_count}

    print(f"{'='*50}")
    print(f"Bible 填写完整度报告")
    print(f"{'='*50}")
    for fname, r in results.items():
        label = files.get(fname, fname)
        if r["status"] == "missing":
            print(f"  ❌ {label}：文件缺失")
        else:
            icon = "✅" if r["filled_pct"] >= 80 else "⚠️" if r["filled_pct"] >= 50 else "❌"
            print(f"  {icon} {label}：{r['filled_pct']}% 已填写（{r['empty']}/{r['total']} 字段空）")
    print(f"  {'─'*50}")
    print(f"  总计：{total_fields} 个字段，{total_empty} 个空字段")
    print(f"{'='*50}")
    return results


def sync_status(project_root: Path):
    """显示同步总览：已写/已同步/timeline/图谱/大纲差距"""
    state_file = project_root / "state" / "current" / "state.json"
    state = read_json(state_file) if state_file.exists() else {}
    progress = state.get("progress", {})
    completed = progress.get("completed_chapters", [])
    synced_to = progress.get("synced_up_to_chapter", 0)
    current = progress.get("current_chapter", 0)

    # 时间线条目数
    tl_file = project_root / "knowledge" / "timeline.md"
    tl_count = 0
    if tl_file.exists():
        tl_count = sum(1 for l in read_md(tl_file).split("\n") if l.startswith("- 第") and "章" in l)

    # 图谱节点数
    graph = load_graph(project_root)
    char_count = sum(1 for n in graph.get("nodes", []) if n["type"] == "character")
    loc_count = sum(1 for n in graph.get("nodes", []) if n["type"] == "location")
    edge_count = len(graph.get("edges", []))

    # 大纲剩余
    outline_file = project_root / "bible" / "03-outline.md"
    last_outline_ch = 0
    if outline_file.exists():
        for line in read_md(outline_file).split("\n"):
            if line.startswith("|") and len(line.split("|")) >= 2:
                try:
                    ch = int(line.split("|")[1].strip())
                    if ch > last_outline_ch:
                        last_outline_ch = ch
                except ValueError:
                    pass

    # 计算未同步章节
    unsynced_count = len([c for c in completed if c > synced_to]) if completed else 0
    ahead_of_outline = max(0, current - last_outline_ch)

    print(f"{'='*50}")
    print(f"  同步状态总览")
    print(f"{'='*50}")
    print(f"  已写章节：{len(completed)} 章" if completed else "  已写章节：0 章")
    print(f"  已同步到：第{synced_to}章")
    if unsynced_count:
        print(f"  ⚠️  未同步：{unsynced_count} 章（运行 post-write）")
    else:
        print(f"  ✅ 全部已同步")
    print(f"  ──────────────────")
    print(f"  时间线条目：{tl_count} 条")
    print(f"  知识图谱：{char_count} 角色, {loc_count} 地点, {edge_count} 关系")
    if last_outline_ch == 0:
        print(f"  大纲：未找到章纲")
    elif last_outline_ch > current:
        print(f"  大纲余量：{last_outline_ch - current} 章")
    else:
        print(f"  ⚠️  大纲已用完（超出 {ahead_of_outline} 章），需 extend-outline")
    print(f"{'='*50}")

    # 检查 bible 完整度（调用 check_bible 但不重新输出）
    bible_dir = project_root / "bible"
    incompleted = []
    if bible_dir.exists():
        for fname in ["00-world-building.md", "01-character-profiles.md"]:
            fpath = bible_dir / fname
            if fpath.exists():
                text = read_md(fpath)
                for line in text.split("\n"):
                    if "（待定）" in line:
                        incompleted.append(fname)
                        break
    if incompleted:
        print(f"  📝 注意：{'、'.join(incompleted)} 中仍有待定字段，运行 check-bible 查看")


def update_estimate(project_root: Path, new_estimate: int):
    """更新 state.json 中的 estimated_chapters"""
    state_file = project_root / "state" / "current" / "state.json"
    if not state_file.exists():
        print(f"  ❌ 未找到 state.json: {state_file}")
        return
    state = read_json(state_file)
    old = state.get("project", {}).get("estimated_chapters", "未设置")
    state.setdefault("project", {})["estimated_chapters"] = new_estimate
    state["last_updated"] = datetime.now().isoformat()
    write_json(state_file, state)
    print(f"  ✅ 目标章节数已更新: {old} → {new_estimate}")


def extend_outline(project_root: Path, add_chapters: int, start_from: int = 0):
    """在 03-outline.md 章纲表格末尾追加新行（自动填充三幕骨架内容）"""
    outline_file = project_root / "bible" / "03-outline.md"
    if not outline_file.exists():
        print(f"  ❌ 未找到大纲文件: {outline_file}")
        return

    text = read_md(outline_file)

    # 找到表格末尾
    table_lines = []
    in_table = False
    for line in text.split("\n"):
        if line.startswith("| 章号 |"):
            in_table = True
            table_lines.append(line)
            continue
        if in_table:
            if line.startswith("|") and "|" in line[1:]:
                table_lines.append(line)
            else:
                in_table = False

    if not table_lines:
        print("  ❌ 未找到章纲表格")
        return

    # 找出已有最后一章的编号
    last_ch = 0
    for line in table_lines[2:]:  # skip header + separator
        parts = line.split("|")
        if len(parts) >= 2:
            try:
                ch = int(parts[1].strip())
                if ch > last_ch:
                    last_ch = ch
            except ValueError:
                pass

    # 判断当前进度所在的幕（优先从大纲标记推断）
    act = 3
    detected_from_outline = False
    for line in reversed(table_lines[2:]):
        parts = line.split("|")
        full_line = line.lower()
        if "第一幕" in full_line or "第1幕" in full_line or "act1" in full_line or "act 1" in full_line:
            act = 1
            detected_from_outline = True
            break
        elif "第二幕" in full_line or "第2幕" in full_line or "act2" in full_line or "act 2" in full_line:
            act = 2
            detected_from_outline = True
            break
        elif "第三幕" in full_line or "第3幕" in full_line or "act3" in full_line or "act 3" in full_line:
            act = 3
            detected_from_outline = True
            break

    if not detected_from_outline:
        if last_ch <= 5:
            act = 1
        elif last_ch <= 15:
            act = 2

    if start_from == 0:
        start_from = last_ch + 1

    # 各幕的轮转模板（4种模式轮换，避免千篇一律）
    act_templates = {
        1: [
            {"goal": "推进主线", "conflict": "冲突浮现", "new_info": "新信息", "hook": "悬念"},
            {"goal": "主角成长", "conflict": "初次阻碍", "new_info": "世界观补充", "hook": "新问题"},
            {"goal": "结识盟友", "conflict": "信任考验", "new_info": "势力格局", "hook": "暗流"},
            {"goal": "深入事件", "conflict": "困境升级", "new_info": "隐藏线索", "hook": "转折"},
        ],
        2: [
            {"goal": "深化矛盾", "conflict": "困境加剧", "new_info": "隐藏信息揭露", "hook": "局势逆转"},
            {"goal": "冲突升级", "conflict": "正面交锋", "new_info": "敌方动机", "hook": "更大阴谋"},
            {"goal": "角色关系深化", "conflict": "信任危机", "new_info": "过往秘密", "hook": "关系转折"},
            {"goal": "危机逼近", "conflict": "两难抉择", "new_info": "关键情报", "hook": "倒计时"},
        ],
        3: [
            {"goal": "推向高潮", "conflict": "最终冲突", "new_info": "关键真相", "hook": "终局悬念"},
            {"goal": "绝地反击", "conflict": "生死对决", "new_info": "终极秘密", "hook": "至暗时刻"},
            {"goal": "收束伏笔", "conflict": "最后阻碍", "new_info": "真相大白", "hook": "结局铺垫"},
            {"goal": "走向结局", "conflict": "最终决战", "new_info": "所有答案", "hook": "大结局"},
        ],
    }

    templates = act_templates.get(act, act_templates[3])

    # 生成新行
    new_rows = []
    for i in range(add_chapters):
        ch = start_from + i
        tpl = templates[i % len(templates)]
        new_rows.append(
            f"| {ch:03d} | | {tpl['goal']} | {tpl['conflict']} | {tpl['new_info']} | {tpl['hook']} |"
        )

    # 插入表格末尾
    insert_pos = text.find(table_lines[-1]) + len(table_lines[-1])
    before = text[:insert_pos]
    after = text[insert_pos:]

    # 在插入前加一个换行（如果后面没有空行）
    if not after.startswith("\n"):
        before += "\n"

    new_text = before + "\n".join(new_rows) + after
    write_md(outline_file, new_text)

    # 同步更新 state.json 的 estimated_chapters
    new_estimate = start_from + add_chapters - 1
    state_file = project_root / "state" / "current" / "state.json"
    if state_file.exists():
        state = read_json(state_file)
        old_est = state.get("project", {}).get("estimated_chapters", 0)
        if new_estimate > old_est:
            state.setdefault("project", {})["estimated_chapters"] = new_estimate
            state["last_updated"] = datetime.now().isoformat()
            write_json(state_file, state)

    print(f"  ✅ 章纲已扩展：新增 {add_chapters} 行（第{start_from}-{new_estimate}章）")
    print(f"     当前处于第{act}幕阶段，已按对应模板填充")
    print(f"     提示：章名和具体内容可手动编辑 bible/03-outline.md")


def list_foreshadowing(project_root: Path, status: str = "open") -> List[dict]:
    """列出伏笔"""
    graph = load_graph(project_root)
    results = []
    for n in graph["nodes"]:
        if n["type"] == "foreshadowing":
            if status == "all" or n.get("properties", {}).get("status", "open") == status:
                results.append(n)
    return results


def update_foreshadowing(project_root: Path, node_id: str, status: str):
    """更新伏笔状态"""
    graph = load_graph(project_root)
    for n in graph["nodes"]:
        if n["id"] == node_id:
            n["properties"]["status"] = status
            n["properties"]["resolved_at"] = datetime.now().isoformat()
            save_graph(project_root, graph)
            print(f"  ✅ 更新伏笔 [{node_id}] 状态 -> {status}")
            return
    print(f"  ❌ 未找到伏笔: {node_id}")


def main():
    parser = argparse.ArgumentParser(description="Novel Master: 知识图谱管理")
    parser.add_argument("--project", "-p", default=".", help="项目根目录")

    sub = parser.add_subparsers(dest="action", required=True)

    # add-node
    p_node = sub.add_parser("add-node", help="添加节点")
    p_node.add_argument("--id", required=True)
    p_node.add_argument("--type", required=True, choices=list(NODE_TYPES.keys()))
    p_node.add_argument("--name", required=True)
    p_node.add_argument("--props", default="{}")
    p_node.add_argument("--chapter", "-c", type=int, default=None, help="引入章节号")

    # add-edge
    p_edge = sub.add_parser("add-edge", help="添加关系")
    p_edge.add_argument("--source", required=True)
    p_edge.add_argument("--target", required=True)
    p_edge.add_argument("--type", required=True, choices=list(EDGE_TYPES.keys()))
    p_edge.add_argument("--props", default="{}")

    # related
    p_rel = sub.add_parser("related", help="查看关联")
    p_rel.add_argument("--id", required=True)

    # check
    sub.add_parser("check", help="一致性检查")

    # foreshadowing
    p_fs = sub.add_parser("foreshadowing", help="伏笔列表")
    p_fs.add_argument("--status", default="open", choices=["open", "resolved", "all"])

    p_fu = sub.add_parser("resolve-fs", help="解决伏笔")
    p_fu.add_argument("--id", required=True)

    # add-attr
    p_attr = sub.add_parser("add-attr", help="添加带章节标记的属性（追踪人物/地点状态变化）")
    p_attr.add_argument("--id", required=True)
    p_attr.add_argument("--key", required=True)
    p_attr.add_argument("--value", required=True)
    p_attr.add_argument("--chapter", "-c", type=int, required=True)

    # check-continuity
    sub.add_parser("check-continuity", help="全面连续性检查（属性矛盾+伏笔超期+悬空边）")

    # brief
    p_brief = sub.add_parser("brief", help="生成写作简报（写前必读，防止跑偏）")
    p_brief.add_argument("--chapter", "-c", type=int, default=0, help="指定章节号（默认下一章）")

    # extend-outline
    p_ext = sub.add_parser("extend-outline", help="扩展章纲表格（追加新行）")
    p_ext.add_argument("--count", "-c", type=int, required=True, help="新增章节数")
    p_ext.add_argument("--start", "-s", type=int, default=0, help="起始章号（默认接续当前末尾）")

    # update-estimate
    p_ue = sub.add_parser("update-estimate", help="更新目标章节数估算")
    p_ue.add_argument("--chapters", "-c", type=int, required=True, help="新的估算章数")

    # post-write
    p_pw = sub.add_parser("post-write", help="写后更新：同步时间线/事件矩阵/检查清单")
    p_pw.add_argument("--chapter", "-c", type=int, default=0, help="刚写完的章节号（默认当前进度）")

    # check-bible
    sub.add_parser("check-bible", help="检查 bible 文件填写完整度")

    # sync-status
    sub.add_parser("sync-status", help="同步总览：已写/已同步/timeline/图谱/大纲差距")

    args = parser.parse_args()
    proj = Path(args.project)

    if args.action == "add-node":
        add_node(proj, args.id, args.type, args.name, json.loads(args.props), args.chapter)
    elif args.action == "add-edge":
        add_edge(proj, args.source, args.target, args.type, json.loads(args.props))
    elif args.action == "add-attr":
        add_attr(proj, args.id, args.key, args.value, args.chapter)
    elif args.action == "related":
        result = get_related(proj, args.id)
        center = result["center"]
        if center:
            print(f"中心：{center['name']} ({NODE_TYPES.get(center['type'], center['type'])})")
            print(f"关联节点 ({len(result['related_nodes'])}):")
            for n in result["related_nodes"]:
                if n:
                    print(f"  - {n['name']} ({NODE_TYPES.get(n['type'], n['type'])})")
        else:
            print("节点未找到")
    elif args.action == "check":
        issues = check_consistency(proj)
        if issues:
            print(f"发现 {len(issues)} 个问题：")
            for i in issues:
                print(f"  ❌ {i}")
        else:
            print("✅ 图谱一致")
    elif args.action == "check-continuity":
        issues = check_continuity(proj)
        if issues:
            print(f"发现 {len(issues)} 个连续性问题：")
            for i in issues:
                print(f"  ❌ {i}")
        else:
            print("✅ 连续性检查通过")
    elif args.action == "brief":
        state_file = proj / "state" / "current" / "state.json"
        chapter = args.chapter
        if chapter == 0 and state_file.exists():
            try:
                state = read_json(state_file)
                chapter = state.get("progress", {}).get("current_chapter", 0) + 1
            except Exception:
                chapter = 1
        if chapter == 0:
            chapter = 1
        brief = generate_brief(proj, chapter)
        print(brief)
    elif args.action == "foreshadowing":
        results = list_foreshadowing(proj, args.status)
        if results:
            print(f"伏笔 ({args.status}):")
            for r in results:
                desc = r.get("properties", {}).get("description", "")
                print(f"  [{r['id']}] {desc}")
        else:
            print("无匹配伏笔")
    elif args.action == "extend-outline":
        extend_outline(proj, args.count, args.start)
    elif args.action == "update-estimate":
        update_estimate(proj, args.chapters)
    elif args.action == "post-write":
        ch = args.chapter
        if ch == 0:
            try:
                state = read_json(proj / "state" / "current" / "state.json")
                ch = state.get("progress", {}).get("current_chapter", 0)
            except Exception:
                ch = 0
        if ch < 1:
            print("❌ 无法确定章节号")
        else:
            post_write(proj, ch)
    elif args.action == "check-bible":
        check_bible(proj)
    elif args.action == "sync-status":
        sync_status(proj)
    elif args.action == "resolve-fs":
        update_foreshadowing(proj, args.id, "resolved")


if __name__ == "__main__":
    main()
