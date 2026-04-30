#!/usr/bin/env python3
"""Novel Master: 质量门禁检查 - 每章强制六步闭环"""

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
        "堆砌比喻": ["像是", "就像", "如同", "犹如", "好似", "宛如"],
        "论文腔": ["不难看出", "由此可见", "事实上", "值得注意的是"],
        "书面腔": ["于是乎", "与此同时", "从而", "因而", "诚然"],
        "一问一答": ["什么情况", "怎么死的", "有发现吗", "查到什么", "你是说", "这说明", "一定是"],
        "信息堆砌": ["工作", "住址", "社交圈", "通话记录", "银行流水", "社交网络"],
        "推理直给": ["不是巧合", "只有一个可能", "这意味着", "不是……而是……", "不是因为", "是因为"],
        "模板句式": ["动作很机械", "脑子里却很", "像是通往另一个", "不长不短", "不多不少", "不远不近", "不轻不重"],
        "模糊指代": ["别的东西", "某种东西", "什么东西", "某个人", "某个地方", "某种方式", "某种感觉"],
        "叠词重叠": ["很长很长", "很远很远", "很久很久", "很深很深", "很慢很慢", "很轻很轻", "很小很小", "很大很大", "很多很多", "好远好远", "好深好深", "好久好久"],
        "空话格言": ["担心也没用", "该做的事情还是得做", "该来的总会来", "一切都会好的", "时间会证明一切", "活着就好", "活着才有希望"],
        "排比否定": ["没有……没有……也没有", "没有……没有……更没有", "没有……没有……也没有"],
        "转折癖": ["但", "可", "却", "然而"],
        "重复强调": ["他来了。他不会走", "不会有事的", "一切都会好的", "别怕。", "撑住。"],
    }

    total_finds = []
    category_counts = {}
    import re

    # 预处理：排比否定句式
    pb_matches = re.findall(r'没有[^。，；！？]{1,20}，没有[^。，；！？]{1,20}，[也更]没有', text)
    if pb_matches:
        category_counts["排比否定"] = len(pb_matches)

    # 预处理：转折癖（以"但/可/却/然而"开头的句子占比）
    sentences_all = re.split(r'[。！？]', text)
    sentences_all = [s.strip() for s in sentences_all if s.strip()]
    but_start = sum(1 for s in sentences_all if s.startswith(('但', '可', '却', '然而')))
    but_ratio = but_start / max(len(sentences_all), 1)
    if but_ratio > 0.08:
        category_counts["转折癖"] = but_start

    # 预处理：重复强调（连续两短句以人称/否定词开头）
    paras = re.split(r'\n\s*\n', text)
    repeat_count = 0
    for para in paras:
        sents = [s.strip() for s in re.split(r'[。！？]', para) if s.strip()]
        for i in range(len(sents) - 1):
            s1, s2 = sents[i], sents[i + 1]
            if len(s1) <= 15 and len(s2) <= 15:
                leaders = {'他', '你', '我', '不', '没', '别', '会', '就', '好'}
                if s1 and s2 and s1[0] in leaders and s2[0] in leaders:
                    repeat_count += 1
    if repeat_count > 0:
        category_counts["重复强调"] = repeat_count

    # 预处理：形容词堆叠（"惨白的阳光""斑驳的地板"等密集出现）
    adj_descriptors = [
        "惨白", "斑驳", "暗红", "苍白", "惨淡", "阴沉", "幽暗",
        "深邃", "朦胧", "模糊", "刺眼", "耀眼", "灼热", "冰冷",
        "阴冷", "寂静", "荒凉", "破败", "残破", "破旧", "陈旧",
        "昏暗", "潮湿", "干燥", "浓稠", "滚烫", "冰凉", "透亮",
        "幽深", "灰暗", "昏黄", "惨白",
    ]
    # 找所有 "形容词+的+名" 模式
    adj_density = 0
    paragraphs = re.split(r'\n\s*\n', text)
    for para in paragraphs:
        para_cn = len(re.findall(r'[一-鿿]', para))
        if para_cn < 30:
            continue  # 太短的段落跳过
        matches = 0
        for adj in adj_descriptors:
            matches += len(re.findall(re.escape(adj) + r'的', para))
        if matches >= 3:
            adj_density += matches
    if adj_density > 0:
        category_counts["形容词堆叠"] = adj_density

    # 普通词频匹配（跳过已预处理过的类别）
    skip_categories = {"排比否定", "转折癖", "重复强调", "形容词堆叠"}
    for category, words in patterns.items():
        if category in skip_categories:
            continue
        count = 0
        for w in words:
            c = text.count(w)
            # 模糊匹配：不是……而是……
            if "不是……而是……" in w:
                c = len(re.findall(r'不是.{0,15}而是', text))
            if c > 0:
                count += c
                total_finds.append((category, w, c))
        if count > 0:
            if category in category_counts:
                category_counts[category] += count
            else:
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


def check_pov_consistency(text: str, project_root: Path) -> Dict:
    """检查叙事人称是否与 bible/02-style-guide.md 声明一致"""
    style_file = project_root / "bible" / "02-style-guide.md"
    if not style_file.exists():
        return {"status": "pass", "skipped": True, "reason": "未找到风格指南"}

    style_text = read_md(style_file)

    declared_pov = None
    for line in style_text.split("\n"):
        line_lower = line.strip().lower()
        if "第一人称" in line:
            declared_pov = "first"
            break
        elif "第三人称" in line:
            declared_pov = "third"
            break
        elif "全知" in line:
            declared_pov = "omniscient"
            break

    if not declared_pov:
        return {"status": "pass", "skipped": True, "reason": "风格指南未声明视角"}

    quote_left = '\u201c\u201d\u2018\u300c\u300e'
    quote_right = '\u201c\u201d\u2019\u300d\u300f'
    stripped = re.sub(f'[{quote_left}].*?[{quote_right}]', '', text)

    first_person_count = len(re.findall(r'(?<![他她它们])我(?!们)', stripped))
    third_person_markers = len(re.findall(r'(?:^|[。！？\n])\s*(?:他|她)(?:的|说|想|看|走|跑|站|坐|笑|哭|把|被|在|从|向|对|给|让|叫|问|答|道|转|抬|低|闭|睁)', stripped))

    if declared_pov == "third" and first_person_count > 3:
        return {
            "status": "fail",
            "declared_pov": "第三人称",
            "detected_issue": f"正文（非对话）中「我」出现 {first_person_count} 次",
            "suggestion": "风格指南声明第三人称，但正文使用了第一人称叙事，请统一",
        }
    elif declared_pov == "first" and third_person_markers > 5 and first_person_count < 3:
        return {
            "status": "fail",
            "declared_pov": "第一人称",
            "detected_issue": f"正文以第三人称叙事为主（第三人称标记 {third_person_markers} 处）",
            "suggestion": "风格指南声明第一人称，但正文使用了第三人称叙事，请统一",
        }

    return {
        "status": "pass",
        "declared_pov": {"first": "第一人称", "third": "第三人称", "omniscient": "全知"}.get(declared_pov, declared_pov),
    }


def check_duplicate_paragraphs(text: str) -> Dict:
    """检测章节内是否存在重复或高度相似的段落"""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip() and len(p.strip()) > 30]

    if len(paragraphs) < 2:
        return {"status": "pass", "duplicates": []}

    duplicates = []
    for i in range(len(paragraphs)):
        for j in range(i + 1, len(paragraphs)):
            p1, p2 = paragraphs[i], paragraphs[j]
            fingerprint_len = min(40, len(p1), len(p2))
            fp1 = p1[:fingerprint_len]
            fp2 = p2[:fingerprint_len]
            if fp1 == fp2:
                duplicates.append({
                    "para_a": i + 1,
                    "para_b": j + 1,
                    "preview": fp1[:50] + "...",
                    "similarity": "exact_start",
                })
                continue

            words1 = set(re.findall(r'[\u4e00-\u9fff]+', p1))
            words2 = set(re.findall(r'[\u4e00-\u9fff]+', p2))
            if not words1 or not words2:
                continue
            intersection = words1 & words2
            union = words1 | words2
            jaccard = len(intersection) / len(union)
            if jaccard > 0.7:
                duplicates.append({
                    "para_a": i + 1,
                    "para_b": j + 1,
                    "preview": p1[:50] + "...",
                    "similarity": round(jaccard, 2),
                })

    status = "fail" if duplicates else "pass"
    suggestion = f"发现 {len(duplicates)} 处重复/高度相似段落，请检查是否为复制遗留" if duplicates else ""

    return {
        "status": status,
        "duplicates": duplicates[:5],
        "suggestion": suggestion,
    }


def check_punctuation(text: str) -> Dict:
    """检查标点符号规范：句号密度、半角混入、省略号/破折号规范、引号配对"""
    import re
    issues = []
    cn_chars = len(re.findall(r'[一-鿿]', text))
    status = "pass"

    # 1. 句号检查
    period_count = text.count('。')
    consecutive_periods = re.findall(r'。{2,}', text)
    if cn_chars > 0:
        if period_count == 0:
            issues.append("全文无句号")
            status = "fail"
        else:
            density = cn_chars / period_count
            if density > 60:
                issues.append(f"句号过少（1句号/{density:.0f}字），可能一逗到底")
                status = "warn" if status != "fail" else status
            elif density < 15:
                issues.append(f"句号过多（1句号/{density:.0f}字），句子碎片化")
                status = "warn" if status != "fail" else status
    if consecutive_periods:
        issues.append(f"连续句号 {len(consecutive_periods)} 处（不允许 ····）")
        status = "fail"

    # 2. 半角标点混入
    halfwidth = re.findall(r'[,.:;!?]', text)
    if halfwidth:
        issues.append(f"混入半角标点 {len(halfwidth)} 处（应使用全角 ，。：；！？）")
        status = "warn" if status != "fail" else status

    # 3. 省略号规范 — 非标准形式
    bad_ellipsis_dots = re.findall(r'(?<!……)\.\.\.(?!……)', text)
    bad_ellipsis_cn = re.findall(r'。{5,}', text)
    if bad_ellipsis_dots:
        issues.append(f"英文省略号 ... 出现 {len(bad_ellipsis_dots)} 处（应使用 ……）")
        status = "warn" if status != "fail" else status
    if bad_ellipsis_cn:
        issues.append(f"连续句号代替省略号 {len(bad_ellipsis_cn)} 处（应使用 ……）")
        status = "warn" if status != "fail" else status

    # 4. 破折号规范
    # 单个 — 但不属于 —— 的一部分
    single_dash = len(re.findall(r'(?<!—)—(?!—)', text))
    if single_dash > 0:
        issues.append(f"单个破折号 {single_dash} 处（应使用 ——）")
        status = "warn" if status != "fail" else status

    # 5. 引号配对
    if text.count('"') > 0 or text.count('"') > 0:
        issues.append('混入英文引号 ""（应使用中文引号 ""）')
        status = "warn" if status != "fail" else status
    left_double = text.count('“')  # "
    right_double = text.count('”')  # "
    left_single = text.count('‘')  # '
    right_single = text.count('’')  # '
    if left_double != right_double:
        issues.append(f"双引号不成对（左{left_double} ≠ 右{right_double}）")
        status = "warn" if status != "fail" else status
    if left_single != right_single:
        issues.append(f"单引号不成对（左{left_single} ≠ 右{left_single}）")
        status = "warn" if status != "fail" else status

    # 6. 引号内句号规则：」他说 / "他说 前不应有句号
    quote_said_pairs = re.findall(r'[。！？][」""]\s*[他她它]\w{0,4}[说问道答喊叫骂]', text)
    if quote_said_pairs:
        issues.append(f"引号内结尾句号/叹号/问号多余 {len(quote_said_pairs)} 处（「你好。」他说 → 「你好」他说）")
        status = "warn" if status != "fail" else status

    # 7. 连续短句句号碎裂检测：两个 <=25字的中文句子用句号断开，后句不以对话开头 -> 建议改逗号
    fragmented_pairs = 0
    paragraphs = re.split(r'\n\s*\n', text)
    for para in paragraphs:
        para_stripped = para.strip()
        if not para_stripped:
            continue
        # 先把引号内容替换为占位符，避免引号内的句号被误伤
        import string
        placeholder_counter = [0]
        quote_placeholders = {}

        def replace_quoted(m):
            ph = f'\x00Q{placeholder_counter[0]}\x00'
            placeholder_counter[0] += 1
            quote_placeholders[ph] = m.group(0)
            return ph

        # 保护引号内容：匹配「」『』""（U+201C/U+201D）""（U+0022）
        q_left = '“‘「『'
        q_right = '”’」』'
        protected = re.sub(f'[{q_left}].*?[{q_right}]', replace_quoted, para)
        # 分割句子
        sentences = re.split(r'[。！？]', protected)
        # 过滤空句
        sentences = [s.strip() for s in sentences if s.strip()]
        for i in range(len(sentences) - 1):
            s1, s2 = sentences[i], sentences[i + 1]
            # 只计中文内容长度
            s1_cn = len(re.findall(r'[一-鿿]', s1))
            s2_cn = len(re.findall(r'[一-鿿]', s2))
            if s1_cn > 0 and s1_cn <= 25 and s2_cn > 0 and s2_cn <= 25:
                # 检查后句是否以对话开头（引号标记）
                s2_stripped = s2.lstrip()
                if not s2_stripped or s2_stripped[0] not in '“‘「『"':
                    fragmented_pairs += 1

    if fragmented_pairs >= 2:
        issues.append(f"连续短句句号碎断开 {fragmented_pairs} 处（<=25字的中文短句用句号断开，建议改为逗号）")
        status = "warn" if status != "fail" else status
    elif fragmented_pairs == 1:
        issues.append(f"短句句号碎开 1 处（<=25字的中文短句用句号断开，建议改为逗号）")
        status = "warn" if status != "fail" else status

    # 8. 破折号数量检测：正常网文不需要大量破折号，用动作描述替代
    em_dash_count = len(re.findall(r'——', text))
    if em_dash_count > 15:
        issues.append(f"破折号过多（{em_dash_count}处），建议改成动作描述或自然叙述，保留≤5处即可")
        status = "fail" if status != "fail" else status
    elif em_dash_count > 8:
        issues.append(f"破折号偏多（{em_dash_count}处），建议减少，保留≤5处即可")
        status = "warn" if status != "fail" else status

    suggestion = ""
    if status != "pass":
        suggestion = "标点问题： " + "；".join(issues[:3])
        if len(issues) > 3:
            suggestion += f" 等{len(issues)}项"

    return {
        "status": status,
        "issues": issues,
        "suggestion": suggestion,
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
    """运行完整六步门禁"""
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
        "punctuation": check_punctuation(text),
        "pov": check_pov_consistency(text, project_root),
        "duplicate": check_duplicate_paragraphs(text),
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
            "punctuation": "标点规范",
            "pov": "视角一致性",
            "duplicate": "重复段落",
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
        elif check_name == "pov":
            if check_result.get("skipped"):
                print(f"    跳过: {check_result.get('reason', '')}")
            elif check_result.get("detected_issue"):
                print(f"    声明: {check_result.get('declared_pov', '?')}")
                print(f"    问题: {check_result['detected_issue']}")
        elif check_name == "duplicate":
            for dup in check_result.get("duplicates", []):
                print(f"    段落{dup['para_a']} ≈ 段落{dup['para_b']}（相似度: {dup['similarity']}）")
                print(f"      预览: {dup['preview']}")
        elif check_name == "punctuation":
            for issue in check_result.get("issues", []):
                print(f"    ⚠ {issue}")

        if check_result.get("suggestion"):
            print(f"    💡 {check_result['suggestion']}")

    if result["overall"] in ("pass", "conditional_pass"):
        print(f"\n  📝 下一步：运行 post-write 同步角色/世界观")
        print(f"     python3 scripts/story_graph.py -p {Path(result['file']).parent.parent} post-write --chapter {result['chapter']}")

    print(f"\n{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Novel Master: 质量门禁检查")
    parser.add_argument("action", choices=["check", "report", "batch"],
                       help="check=检查最新/指定章节, report=显示所有章节门禁摘要, batch=批量检查+汇总")
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

    elif args.action == "batch":
        files = get_chapter_files(proj)
        if not files:
            print("暂无章节")
            return
        if args.chapter > 0:
            files = [f for f in files if chapter_number(f.name) >= args.chapter]
        results = []
        for f in files:
            result = run_full_gate(proj, f)
            results.append(result)
        print(f"\n{'='*60}")
        print(f"  批量门禁报告（{len(results)} 章）")
        print(f"{'='*60}")
        emoji = {"pass": "\u2705", "fail": "\u274c", "conditional_pass": "\u26a0\ufe0f"}
        for r in results:
            overall = r["overall"]
            ch = r.get("chapter", "?")
            fails = [k for k, v in r.get("checks", {}).items() if v.get("status") == "fail"]
            warns = [k for k, v in r.get("checks", {}).items() if v.get("status") == "warn"]
            detail = ""
            if fails:
                detail += f"  FAIL: {','.join(fails)}"
            if warns:
                detail += f"  WARN: {','.join(warns)}"
            print(f"  {emoji.get(overall, '?')} 第{ch:03d}章: {overall}{detail}")
        total_pass = sum(1 for r in results if r["overall"] == "pass")
        total_cp = sum(1 for r in results if r["overall"] == "conditional_pass")
        total_fail = sum(1 for r in results if r["overall"] == "fail")
        print(f"\n  通过: {total_pass}  条件通过: {total_cp}  失败: {total_fail}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
