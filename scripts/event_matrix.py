#!/usr/bin/env python3
"""Novel Master: 事件矩阵管理 - 冷却跟踪、节奏检测"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils import read_json, write_json, get_chapter_files, read_md


EVENT_TYPES = {
    "conflict_thrill": "冲突高潮",
    "bond_deepening": "情感升温",
    "faction_building": "势力构建",
    "world_painting": "世界观展示",
    "tension_escalation": "危机升级",
}

DEFAULT_COOLDOWNS = {
    "conflict_thrill": 2,
    "bond_deepening": 1,
    "faction_building": 2,
    "world_painting": 3,
    "tension_escalation": 2,
}


def load_matrix(project_root: Path) -> dict:
    path = project_root / "knowledge" / "event_matrix.json"
    if path.exists():
        return read_json(path)
    return {"events": [], "cooldowns": dict(DEFAULT_COOLDOWNS), "config": {"min_bond_or_world_every_n": 5}}


def save_matrix(project_root: Path, matrix: dict):
    matrix["last_updated"] = datetime.now().isoformat()
    write_json(project_root / "knowledge" / "event_matrix.json", matrix)


def add_event(project_root: Path, chapter: int, event_type: str, description: str):
    """记录一个事件"""
    matrix = load_matrix(project_root)
    matrix["events"].append({
        "chapter": chapter,
        "type": event_type,
        "description": description,
        "timestamp": datetime.now().isoformat(),
    })
    save_matrix(project_root, matrix)
    print(f"  ✅ 记录事件 [{EVENT_TYPES.get(event_type, event_type)}] 第{chapter}章: {description}")


def check_cooldowns(project_root: Path, current_chapter: int) -> List[str]:
    """检查当前可用的事件类型（不在冷却中的）"""
    matrix = load_matrix(project_root)
    cooldowns = matrix.get("cooldowns", DEFAULT_COOLDOWNS)

    # 获取最近的事件
    recent = sorted(matrix["events"], key=lambda e: e["chapter"], reverse=True)

    available = []
    for etype, name in EVENT_TYPES.items():
        cd = cooldowns.get(etype, 2)
        # 找这个类型最近出现章
        last_use = None
        for e in recent:
            if e["type"] == etype:
                last_use = e["chapter"]
                break
        if last_use is None or (current_chapter - last_use) >= cd:
            available.append(etype)

    return available


def check_rhythm(project_root: Path) -> Dict:
    """检查节奏健康度"""
    matrix = load_matrix(project_root)
    events = matrix["events"]
    config = matrix.get("config", {})

    if not events:
        return {"status": "ok", "message": "暂无事件记录"}

    warnings = []
    max_chapter = max(e["chapter"] for e in events)

    # 检查：每5章至少包含1个情感/世界观事件
    min_interval = config.get("min_bond_or_world_every_n", 5)
    for start in range(1, max_chapter + 1, min_interval):
        end = min(start + min_interval - 1, max_chapter)
        chunk_events = [e for e in events if start <= e["chapter"] <= end]
        has_soft = any(e["type"] in ("bond_deepening", "world_painting") for e in chunk_events)
        if not has_soft:
            warnings.append(f"第{start}-{end}章缺少情感升温或世界观展示事件")

    # 统计事件分布
    type_counts = {}
    for e in events:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1

    return {
        "status": "warning" if warnings else "ok",
        "total_events": len(events),
        "type_distribution": {EVENT_TYPES.get(k, k): v for k, v in type_counts.items()},
        "warnings": warnings,
        "cooldown_status": check_cooldowns(project_root, max_chapter + 1),
    }


def suggest_next_event(project_root: Path, current_chapter: int, context: str = "") -> str:
    """推荐下一章的事件类型"""
    available = check_cooldowns(project_root, current_chapter)

    if not available:
        return "conflict_thrill"

    # 优先推荐与前几章不同的事件
    matrix = load_matrix(project_root)
    recent_events = sorted(matrix["events"], key=lambda e: e["chapter"], reverse=True)[:2]
    recent_types = [e["type"] for e in recent_events]

    # 去掉刚用过的
    candidates = [t for t in available if t not in recent_types]
    if not candidates:
        candidates = available

    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description="Novel Master: 事件矩阵管理")
    parser.add_argument("action", choices=["add", "check", "rhythm", "suggest"],
                       help="操作: add=记录事件, check=检查冷却, rhythm=节奏检测, suggest=推荐事件")
    parser.add_argument("--project", "-p", default=".", help="项目根目录")
    parser.add_argument("--chapter", "-c", type=int, default=0, help="章节号")
    parser.add_argument("--type", "-t", choices=list(EVENT_TYPES.keys()), help="事件类型")
    parser.add_argument("--desc", "-d", default="", help="事件描述")

    args = parser.parse_args()
    proj = Path(args.project)

    if args.action == "add":
        if not args.type or not args.desc:
            print("❌ add 操作需要 --type 和 --desc")
            return
        add_event(proj, args.chapter, args.type, args.desc)

    elif args.action == "check":
        chapter = args.chapter or len(get_chapter_files(proj)) + 1
        available = check_cooldowns(proj, chapter)
        print(f"第{chapter}章可用事件类型：")
        for t in available:
            print(f"  ✅ {EVENT_TYPES.get(t, t)}")
        unavailable = [t for t in EVENT_TYPES if t not in available]
        if unavailable:
            print("冷却中：")
            for t in unavailable:
                print(f"  ⏳ {EVENT_TYPES.get(t, t)}")

    elif args.action == "rhythm":
        result = check_rhythm(proj)
        print(f"节奏状态：{result['status']}")
        if "total_events" in result:
            print(f"总事件数：{result['total_events']}")
            print(f"分布：{result['type_distribution']}")
        if result.get("warnings"):
            print("\n⚠️  警告：")
            for w in result["warnings"]:
                print(f"  {w}")

    elif args.action == "suggest":
        chapter = args.chapter or len(get_chapter_files(proj)) + 1
        suggestion = suggest_next_event(proj, chapter, args.desc)
        print(f"第{chapter}章推荐事件类型：{EVENT_TYPES.get(suggestion, suggestion)}")


if __name__ == "__main__":
    main()
