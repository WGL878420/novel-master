#!/usr/bin/env python3
"""Novel Master: 质量门禁检查 - 每章强制五步闭环"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils import (
    read_json, write_json, read_md, get_chapter_files, count_chinese_chars,
    get_latest_chapter, chapter_number, get_word_limits_for_chapter, get_phase_name,
    summary_from_chapter,
)


def check_word_count(text: str, chapter_num: int = 0, writing_type: str = "medium") -> Dict:
    """字数检查（铁律：必须一次性写满，绝不事后补字数）"""
    min_words, max_words = get_word_limits_for_chapter(writing_type, chapter_num)
    count = count_chinese_chars(text)
    phase = get_phase_name(writing_type, chapter_num)

    status = "pass" if min_words <= count <= max_words else "fail"
    issues = []
    is_iron_rule_violation = False
    if count < min_words:
        issues.append(f"字数不足（{count} < {min_words}）")
        is_iron_rule_violation = True
    elif count > max_words:
        issues.append(f"字数超限（{count} > {max_words}）")
    result = {"status": status, "count": count, "min": min_words, "max": max_words, "issues": issues, "iron_rule": is_iron_rule_violation}
    if phase:
        result["phase"] = phase
    return result


def check_hook(text: str) -> Dict:
    """检查章末是否有钩子"""
    # 取最后300字
    tail = text[-300:] if len(text) > 300 else text
    # 检查疑问句
    has_question = "?" in tail or "？" in tail or "吗" in tail or "呢" in tail or "什么" in tail
    # 检查转折词
    has_twist_words = any(w in tail for w in ["突然", "没想到", "却发现", "原来", "可是", "但是", "然而", "竟"])
    # 检查行动中断
    has_action_break = any(w in tail for w in ["——", "…", "..."])
    # 检查未完成感
    has_cliff = has_question or has_twist_words or has_action_break

    score = 0
    if has_question:
        score += 2
    if has_twist_words:
        score += 2
    if has_action_break:
        score += 1

    return {
        "status": "pass" if score >= 2 else "warn" if score >= 1 else "fail",
        "score": score,
        "details": {
            "has_question": has_question,
            "has_twist": has_twist_words,
            "has_cliffhang": has_action_break,
        },
        "suggestion": "" if score >= 2 else "章末缺少悬念钩子，考虑添加疑问、转折或未完成动作",
    }


def check_opening_grab(text: str) -> Dict:
    """检查开头是否抓人"""
    # 取前300字
    head = text[:300] if len(text) > 300 else text
    # 检查是否有对话
    has_dialogue = bool(re.search(r'["“‘「]', head))
    # 检查是否有动作
    has_action = any(w in head for w in ["冲", "踢", "抓", "跑", "打", "喊", "推", "拉", "拔", "跳"])
    # 检查是否直接进入冲突
    has_conflict = any(w in head for w in ["危机", "危险", "追杀", "背叛", "秘密", "死亡", "阴谋", "陷阱"])

    score = sum([has_dialogue, has_action, has_conflict])
    return {
        "status": "pass" if score >= 2 else "warn" if score >= 1 else "fail",
        "score": score,
        "details": {"has_dialogue": has_dialogue, "has_action": has_action, "has_conflict": has_conflict},
        "suggestion": "" if score >= 2 else "开头缺乏抓力，考虑以对话、动作或直接冲突开场",
    }


def check_ai_indicators(text: str) -> Dict:
    """检查AI味指标"""
    patterns = {
        "高频AI词": ["不禁", "仿佛", "映入眼帘", "心中暗道", "沉声道", "脸色一变", "嘴角微扬", "不由自主", "只见", "此时此刻"],
        "弱副词": ["微微", "淡淡", "缓缓", "轻轻", "悄然", "默默", "隐隐"],
        "论文腔": ["不难看出", "由此可见", "事实上", "值得注意的是"],
        "书面腔": ["于是乎", "与此同时", "从而", "因而", "诚然"],
        "一问一答": ["什么情况", "怎么死的", "有发现吗", "查到什么", "你是说", "这说明", "一定是"],
        "信息堆砌": ["工作", "住址", "社交圈", "通话记录", "银行流水", "社交网络"],
        "推理直给": ["不是巧合", "只有一个可能", "这意味着"],
    }

    total_finds = []
    category_counts = {}
    for category, words in patterns.items():
        count = 0
        for w in words:
            c = text.count(w)
            if c > 0:
                count += c
                total_finds.append((category, w, c))
        if count > 0:
            category_counts[category] = count

    # 每千字AI词密度
    char_count = count_chinese_chars(text)
    density = sum(category_counts.values()) / max(char_count, 1) * 1000

    return {
        "status": "pass" if density < 3 else "warn" if density < 6 else "fail",
        "density": round(density, 2),
        "total_hits": sum(category_counts.values()),
        "category_counts": category_counts,
        "details": total_finds[:10],  # 最多列10个
        "suggestion": "" if density < 3 else f"AI味指标偏高（{density:.1f}/千字），建议用具体动作和对话替代抽象描述",
    }


def check_conflict(text: str) -> Dict:
    """检查章节是否有冲突"""
    conflict_words = ["冲突", "争执", "对决", "战斗", "对抗", "反对", "不同意", "愤怒",
                      "生气", "挣扎", "两难", "抉择", "危机", "危险", "威胁",
                      "背叛", "欺骗", "陷阱", "争吵", "打斗"]
    found = sum(1 for w in conflict_words if w in text)
    return {
        "status": "pass" if found >= 3 else "warn" if found >= 1 else "fail",
        "found": found,
        "suggestion": "" if found >= 3 else "本章缺乏明显冲突，考虑增加对抗或困境",
    }


def update_project_state(project_root: Path, chapter_num: int, gate_result: Dict):
    """章节通过门禁后，更新 state.json 的进度和摘要"""
    state_file = project_root / "state" / "current" / "state.json"
    if not state_file.exists():
        return

    state = read_json(state_file)

    # 更新进度
    completed = state["progress"].get("completed_chapters", [])
    if chapter_num not in completed:
        completed.append(chapter_num)
    state["progress"]["completed_chapters"] = sorted(completed)
    state["progress"]["current_chapter"] = chapter_num
    state["progress"]["status"] = "writing"

    # 从章节文件提取摘要
    ch_file = project_root / "manuscript" / f"第{chapter_num:03d}章-*.md"
    from glob import glob
    matches = list(project_root.glob(f"manuscript/第{chapter_num:03d}章-*.md"))
    if matches:
        text = read_md(matches[0])
        summary = summary_from_chapter(text, max_chars=300)
        events = state["summary"].get("latest_events", [])
        # 只保留最近的5条
        events.insert(0, summary)
        state["summary"]["latest_events"] = events[:5]

    state["last_updated"] = datetime.now().isoformat()
    write_json(state_file, state)


def run_full_gate(project_root: Path, chapter_file: Optional[Path] = None) -> Dict:
    """运行完整五步门禁"""
    if chapter_file is None:
        chapter_file = get_latest_chapter(project_root)

    if not chapter_file or not chapter_file.exists():
        return {"status": "fail", "error": "未找到章节文件"}

    text = read_md(chapter_file)
    chapter_num = chapter_number(chapter_file.name)

    # 读取写作类型配置
    state_file = project_root / "state" / "current" / "state.json"
    writing_type = "medium"
    if state_file.exists():
        state = read_json(state_file)
        writing_type = state.get("project", {}).get("writing_type", "medium")

    checks = {
        "word_count": check_word_count(text, chapter_num=chapter_num, writing_type=writing_type),
        "opening": check_opening_grab(text),
        "hook": check_hook(text),
        "ai_indicators": check_ai_indicators(text),
        "conflict": check_conflict(text),
    }

    # 总判断
    all_pass = all(c["status"] == "pass" for c in checks.values())
    has_fail = any(c["status"] == "fail" for c in checks.values())

    result = {
        "chapter": chapter_num,
        "file": str(chapter_file),
        "timestamp": datetime.now().isoformat(),
        "overall": "pass" if all_pass else "fail" if has_fail else "conditional_pass",
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks.values() if c["status"] == "pass"),
            "warnings": sum(1 for c in checks.values() if c["status"] == "warn"),
            "failed": sum(1 for c in checks.values() if c["status"] == "fail"),
        },
    }

    # 保存门禁记录（铁律违反时不保存——字数不够必须重写）
    if result["overall"] != "fail" or not result["checks"]["word_count"].get("iron_rule"):
        gates_dir = project_root / "gates"
        gates_dir.mkdir(exist_ok=True)
        gate_file = gates_dir / f"第{chapter_num:03d}章-gate.json"
        write_json(gate_file, result)

    # 铁律违反：字数不够，不更新 state、不写门禁记录
    if result["checks"]["word_count"].get("iron_rule"):
        return result

    # 门禁通过后自动更新 state.json
    if result["overall"] in ("pass", "conditional_pass"):
        update_project_state(project_root, chapter_num, result)

    return result


def print_gate_result(result: Dict):
    """打印门禁结果"""
    if "error" in result:
        print(f"❌ {result['error']}")
        return

    # 字数铁律违反：直接显示错误，不显示其他检查
    if result["checks"]["word_count"].get("iron_rule"):
        wc = result["checks"]["word_count"]
        print(f"\n{'='*50}")
        print(f"❌ 第{result['chapter']:03d}章 未通过字数铁律")
        print(f"{'='*50}")
        print(f"   中文字数：{wc['count']}（目标：{wc['min']}-{wc['max']}）")
        print(f"{'!'*50}")
        print(f"   ⚠ 铁律：必须一次性写满 {wc['min']}-{wc['max']} 字")
        print(f"   ⚠ 不允许事后补充字数")
        print(f"   ⚠ 请删除本章后重写")
        print(f"{'!'*50}\n")
        return

    emoji = {"pass": "✅", "fail": "❌", "conditional_pass": "⚠️"}
    print(f"\n{'='*50}")
    print(f"第{result['chapter']:03d}章 质量门禁报告")
    print(f"{'='*50}")
    print(f"总体状态: {emoji.get(result['overall'], '?')} {result['overall']}")
    print(f"通过: {result['summary']['passed']}/{result['summary']['total_checks']}")
    if result['summary']['warnings']:
        print(f"警告: {result['summary']['warnings']}")
    if result['summary']['failed']:
        print(f"失败: {result['summary']['failed']}")

    for check_name, check_result in result["checks"].items():
        c_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        labels = {
            "word_count": "字数检查",
            "opening": "开头抓力",
            "hook": "章末钩子",
            "ai_indicators": "AI味检测",
            "conflict": "冲突检测",
        }
        status = check_result["status"]
        print(f"\n  {c_emoji.get(status, '?')} {labels.get(check_name, check_name)}: {status}")
        if status == "pass":
            continue
        if check_name == "word_count":
            phase_info = f" ({check_result.get('phase', '')})" if check_result.get("phase") else ""
            print(f"    字数: {check_result['count']} / 目标: {check_result['min']}-{check_result['max']}{phase_info}")
        elif check_name == "ai_indicators":
            print(f"    密度: {check_result['density']}/千字")
            for cat, cnt in check_result.get("category_counts", {}).items():
                print(f"    {cat}: {cnt}处")
        elif check_name == "hook":
            print(f"    得分: {check_result['score']}/4")
        elif check_name == "opening":
            print(f"    得分: {check_result['score']}/3")
        elif check_name == "conflict":
            print(f"    冲突词出现: {check_result['found']}处")

        if check_result.get("suggestion"):
            print(f"    💡 {check_result['suggestion']}")

    if result["overall"] in ("pass", "conditional_pass"):
        print(f"\n  📝 下一步：运行 post-write 同步角色/世界观")
        print(f"     python3 scripts/story_graph.py -p {Path(result['file']).parent.parent} post-write --chapter {result['chapter']}")

    print(f"\n{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Novel Master: 质量门禁检查")
    parser.add_argument("action", choices=["check", "report"],
                       help="check=检查最新/指定章节, report=显示所有章节门禁摘要")
    parser.add_argument("--project", "-p", default=".", help="项目根目录")
    parser.add_argument("--chapter", "-c", type=int, default=0, help="指定章节号")

    args = parser.parse_args()
    proj = Path(args.project)

    if args.action == "check":
        chapter_file = None
        if args.chapter > 0:
            files = get_chapter_files(proj)
            for f in files:
                if chapter_number(f.name) == args.chapter:
                    chapter_file = f
                    break
            if not chapter_file:
                print(f"未找到第{args.chapter}章")
                return
        result = run_full_gate(proj, chapter_file)
        print_gate_result(result)
        if result["overall"] == "fail" or result.get("checks", {}).get("word_count", {}).get("iron_rule"):
            import sys
            sys.exit(1)

    elif args.action == "report":
        files = get_chapter_files(proj)
        if not files:
            print("暂无章节")
            return
        for f in files:
            result = run_full_gate(proj, f)
            emoji = {"pass": "✅", "fail": "❌", "conditional_pass": "⚠️"}
            overall = result["overall"]
            print(f"第{result['chapter']:03d}章: {emoji.get(overall, '?')} {overall}")


if __name__ == "__main__":
    main()
