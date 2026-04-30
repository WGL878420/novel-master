#!/usr/bin/env python3
"""Novel Master: AI味检测与去AI味工具

整合自：
- leenbj/novel-creator-skill 的 7 分类检测
- op7418/Humanizer-zh 的 24 种模式
- Tomsawyerhu/Chinese-WebNovel-Skill 的去AI味原则
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from utils import read_md, count_chinese_chars


# ========== 检测模式 ==========

AI_PATTERNS = {
    "高频AI词汇": {
        "weight": 2,
        "words": [
            "不禁", "仿佛", "宛如", "宛若", "映入眼帘", "心中暗道",
            "暗自思忖", "沉声道", "淡淡地说", "脸色一变", "身形一顿",
            "嘴角微扬", "勾起一抹", "不由自主", "情不自禁", "只见",
            "此时此刻", "目光如炬", "目光深邃", "眼底", "眸中",
            "心头一紧", "心头一暖", "心中一沉", "冷哼一声",
        ],
    },
    "弱副词滥用": {
        "weight": 1,
        "words": [
            "微微", "淡淡", "缓缓", "轻轻", "悄然", "默默", "隐隐",
            "稍稍", "略略", "渐渐", "幽幽",
        ],
    },
    "意义膨胀": {
        "weight": 2,
        "words": [
            "意义深远", "前所未有", "可谓", "堪称", "无疑", "注定",
            "彻底改变", "划时代", "里程碑", "至关重要",
        ],
    },
    "套话结语": {
        "weight": 2,
        "words": [
            "未来可期", "前途无量", "充满希望", "一切都是最好的安排",
            "生活还要继续", "明天会更好",
        ],
    },
    "论文腔开头": {
        "weight": 1,
        "words": [
            "不难看出", "由此可见", "事实上", "值得注意的是",
            "不可否认的是", "显而易见", "毋庸置疑",
        ],
    },
    "书面腔": {
        "weight": 1,
        "words": [
            "于是乎", "与此同时", "从而", "因而", "诚然",
            "一方面……另一方面", "与其……不如",
        ],
    },
    "三重排比": {
        "weight": 2,
        "is_regex": True,
        "patterns": [
            # 检测连续三个短句结构（X，Y，Z，）
            r"([^，。！？\n]{2,10}，){3}",
        ],
    },
    "情绪解释过多": {
        "weight": 2,
        "words": [
            "她感到", "他感觉", "她心中", "他内心", "她的心里",
            "一股莫名的", "一种说不出的", "一种复杂的",
            "百感交集", "五味杂陈", "心情复杂",
        ],
    },
    "AI 常用句式": {
        "weight": 1,
        "words": [
            "仿佛凝固", "空气安静", "时间静止", "气氛微妙",
            "说不清道不明", "说不出的", "难以言喻",
            "一股寒意", "一股暖流",
        ],
    },
    "过度修饰": {
        "weight": 1,
        "words": [
            "清冷", "深邃", "低沉", "磁性", "邪魅", "俊美",
            "绝美", "倾国倾城", "风华绝代",
        ],
        "context": "网文可用但不宜堆砌，连续出现3个以上需注意",
    },
    "一问一答式对话": {
        "weight": 2,
        "words": [
            "什么情况", "怎么死的", "脖子上是什么", "有发现吗",
            "什么发现", "结果呢", "查到什么", "怎么不一样",
            "你是说", "你的意思是",
        ],
        "context": "对话变成纯信息交换，缺少潜台词和情绪。真实对话应该带情绪输出，不直接回答问题",
    },
    "完美逻辑链": {
        "weight": 2,
        "words": [
            "第一个可能是", "第二个就有可能是", "第三个就一定是",
            "第一起...第二起...第三起",
            "首先...其次...最后",
            "一是...二是...三是",
        ],
        "context": "推理过程太顺滑，缺少试错和犹豫。人类探案是碎片的、混乱的",
    },
    "信息堆砌": {
        "weight": 2,
        "words": [
            "通话记录", "社交网络", "银行流水",
            "现场照片", "尸检报告", "调查记录",
            "工作", "住址", "社交圈",
        ],
        "context": "一次性抛出一串线索清单，像工作汇报不像对话",
    },
    "推理结论直给": {
        "weight": 1,
        "words": [
            "这说明", "由此可见", "这就意味着",
            "不是巧合", "一定是", "只有一个可能",
        ],
        "context": "推理跳跃太大，缺少中间思考环节。要允许主角猜错、犹豫",
    },
}


def detect_chapter(text: str) -> Dict:
    """完整检测一章的AI味"""
    results = {}
    total_hits = 0
    total_weighted = 0
    details = []

    for category, config in AI_PATTERNS.items():
        hits = []
        weight = config.get("weight", 1)

        # 词汇匹配
        for word in config.get("words", []):
            count = text.count(word)
            if count > 0:
                hits.append({"word": word, "count": count})

        # 正则匹配
        if config.get("is_regex"):
            for pattern in config.get("patterns", []):
                matches = re.findall(pattern, text)
                if matches:
                    hits.append({"pattern": pattern, "count": len(matches)})

        category_hits = sum(h["count"] for h in hits)
        total_hits += category_hits
        total_weighted += category_hits * weight

        if category_hits > 0:
            results[category] = {
                "hits": category_hits,
                "score": category_hits * weight,
                "details": hits,
            }
            details.extend(hits)

    return {
        "total_hits": total_hits,
        "weighted_score": total_weighted,
        "categories": results,
        "details": details,
    }


def assess_quality(detect_result: Dict, total_chars: int, threshold: float = 3.0) -> Dict:
    """综合评估文本质量（使用加权密度判定）"""
    hits = detect_result["total_hits"]
    weighted = detect_result["weighted_score"]
    density = hits / max(total_chars, 1) * 1000
    weighted_density = weighted / max(total_chars, 1) * 1000

    if weighted_density <= threshold * 0.33:
        level = "优秀"
        verdict = "pass"
    elif weighted_density <= threshold:
        level = "良好"
        verdict = "pass"
    elif weighted_density <= threshold * 2:
        level = "需优化"
        verdict = "warn"
    else:
        level = "AI味重"
        verdict = "fail"

    return {
        "verdict": verdict,
        "level": level,
        "density": round(density, 2),
        "weighted_density": round(weighted_density, 2),
        "total_hits": hits,
        "score": weighted,
    }


def generate_report(detect_result: Dict, total_chars: int, threshold: float = 3.0) -> str:
    """生成可读报告"""
    quality = assess_quality(detect_result, total_chars, threshold=threshold)
    lines = []
    lines.append(f"## AI味检测报告\n")
    lines.append(f"**总体评估**: {quality['level']}")
    lines.append(f"**AI词密度**: {quality['density']}/千字")
    lines.append(f"**命中总数**: {quality['total_hits']}\n")

    if detect_result["categories"]:
        lines.append("### 分类详情\n")
        sorted_cats = sorted(
            detect_result["categories"].items(),
            key=lambda x: x[1]["score"],
            reverse=True,
        )
        for cat, info in sorted_cats:
            lines.append(f"- **{cat}**: {info['hits']}处 (得分{info['score']})")
            for d in info["details"]:
                if "word" in d:
                    lines.append(f"  - 「{d['word']}」出现{d['count']}次")
            lines.append("")

    if quality["verdict"] != "pass":
        lines.append("### 优化建议\n")
        lines.append("1. **高频词** → 替换为具体动作或感官描写")
        lines.append("2. **弱副词** → 删掉或替换为具体程度")
        lines.append("3. **情绪解释** → 用动作和对话表现，不用抽象总结")
        lines.append("4. **书面腔** → 改为口语化表达")
        lines.append("5. **三重排比** → 压缩为一句话")
        lines.append("")
        lines.append("去AI味原则：能用动作不用总结，能用对白不用解释，能写具体不写抽象。")

    return "\n".join(lines)


def two_pass_polish(text: str, threshold: float = 3.0) -> Dict:
    """两遍润色法（输出提示，不直接改原文）"""
    detect = detect_chapter(text)
    quality = assess_quality(detect, count_chinese_chars(text), threshold=threshold)

    polish_prompt_parts = []

    # Pass 1: 清除明确的AI模式
    pass1_items = []
    for cat, info in detect.get("categories", {}).items():
        if info["hits"] >= 2:
            pass1_items.append(f"  - {cat}: {info['hits']}处")
    if pass1_items:
        polish_prompt_parts.append("### 第一遍：清除AI模式")
        polish_prompt_parts.append("逐段检查并替换以下模式：")
        polish_prompt_parts.extend(pass1_items)

    # Pass 2: AI自审
    if quality["verdict"] != "pass":
        polish_prompt_parts.append("\n### 第二遍：AI自审")
        polish_prompt_parts.append("通读全文，找出3-5处最明显的AI痕迹，逐处改写。")
        polish_prompt_parts.append("改写原则：保持原意的同时增加具体性、动作感和人物个性。")

    return {
        "quality": quality,
        "polish_prompt": "\n".join(polish_prompt_parts),
        "needs_polish": quality["verdict"] != "pass",
    }


def main():
    parser = argparse.ArgumentParser(description="Novel Master: AI味检测")
    parser.add_argument("action", choices=["detect", "report", "polish"],
                       help="detect=检测, report=生成报告, polish=生成润色提示")
    parser.add_argument("file", help="章节文件路径")
    parser.add_argument("--threshold", "-t", type=float, default=3.0,
                       help="告警阈值(每千字命中数)，默认3.0")

    args = parser.parse_args()
    text = read_md(Path(args.file))
    cn_chars = count_chinese_chars(text)

    if args.action == "detect":
        result = detect_chapter(text)
        quality = assess_quality(result, cn_chars, threshold=args.threshold)
        print(json.dumps({"quality": quality, "categories": result["categories"]},
                        ensure_ascii=False, indent=2))

    elif args.action == "report":
        result = detect_chapter(text)
        report = generate_report(result, cn_chars, threshold=args.threshold)
        print(report)

    elif args.action == "polish":
        result = two_pass_polish(text, threshold=args.threshold)
        print(f"质量评估: {result['quality']['level']}")
        print(f"需要润色: {'是' if result['needs_polish'] else '否'}")
        if result["polish_prompt"]:
            print("\n" + result["polish_prompt"])


if __name__ == "__main__":
    main()
