#!/usr/bin/env python3
"""Novel Master: 项目初始化脚本 - 创建新小说项目的完整目录结构"""

import argparse
from datetime import datetime
from pathlib import Path

from utils import ensure_dir, write_json, write_md, WRITING_TYPES, get_writing_type_config


def _detect_genre_keywords(genre: str) -> set:
    """从题材字符串中提取关键词"""
    keywords = set()
    mapping = {
        "穿越": ["穿越", "古代", "重生", "回"],
        "悬疑": ["悬疑", "推理", "探案", "破案", "刑侦", "侦探", "谋杀", "犯罪"],
        "系统": ["系统", "游戏", "升级", "面板", "任务", "技能"],
        "都市": ["都市", "现代", "职场", "校园", "娱乐"],
        "玄幻": ["玄幻", "修仙", "修真", "仙侠", "魔法", "斗气"],
        "历史": ["历史", "唐朝", "宋朝", "明朝", "清朝", "三国", "战国"],
        "言情": ["言情", "爱情", "甜宠", "虐恋", "婚恋"],
        "科幻": ["科幻", "未来", "星际", "赛博", "末世"],
        "恐怖": ["恐怖", "惊悚", "灵异", "鬼怪"],
    }
    for key, words in mapping.items():
        for w in words:
            if w in genre:
                keywords.add(key)
                break
    return keywords or {"通用"}


def _chapter_outline(initial_estimate: int) -> list:
    """生成章纲骨架（初始仅生成前半部分作为起点，后续可扩展）"""
    # 只生成前 min(15, initial_estimate) 章作为起点，不写死总长度
    starter_count = min(15, max(10, initial_estimate))
    act1_end = max(1, starter_count // 4)
    act2_end = max(act1_end + 1, starter_count * 3 // 4)

    chapters = []
    for i in range(1, starter_count + 1):
        entry = {"chapter": i, "title": "", "goal": "", "conflict": "", "new_info": "", "hook": ""}
        if i == 1:
            entry.update({"title": "开端", "goal": "引入主角和故事背景", "conflict": "初始困境", "new_info": "世界观初步展示", "hook": "第一个冲突出现"})
        elif i <= act1_end:
            entry.update({"title": "", "goal": "推进主线", "conflict": "冲突升级", "new_info": "新线索浮现", "hook": "悬念"})
        elif i <= act2_end:
            entry.update({"title": "", "goal": "深化矛盾", "conflict": "困境加剧", "new_info": "隐藏信息揭露", "hook": "局势逆转"})
        else:
            entry.update({"title": "", "goal": "推向高潮", "conflict": "最终冲突", "new_info": "关键真相", "hook": "终局悬念"})
        chapters.append(entry)
    return chapters


def _content_world_building(name: str, genre: str, author: str, keywords: set) -> str:
    """生成世界观设定（字段内容已填充，非空壳）"""
    core = name.replace("系统", "").strip()
    if not core:
        core = "神探"
    system_name = f"【{core}】"
    lines = [
        f"# 世界观设定\n",
        f"## 基本信息",
        f"- **小说**：{name}",
        f"- **题材**：{genre}",
        f"- **作者**：{author or '佚名'}\n",
    ]
    # 世界背景（通用）
    lines += [
        "## 世界背景",
        "### 时代/年代",
        "唐代（贞观年间），公元630年前后，正值大唐盛世",
        "",
        "### 地理分布",
        "核心舞台：长安城（皇城、东西两市、坊间里巷）",
        "扩展区域：长安周边县城、洛阳、江南道（后续剧情可能涉及）",
        "",
        "### 阵营/势力",
        "- 大理寺：朝廷司法机构，主角所属阵营",
        "- 长安县衙：地方官府，与大理寺存在职权摩擦",
        "- 东西两市商会：长安商业势力，涉及走私、黑市",
        "- 朝中势力：分属不同派系，案件背后常有朝堂暗流",
        "",
        "### 社会规则",
        "- 大唐律法森严，但权贵可一定程度凌驾于法律之上",
        "- 长安实行宵禁制度，夜间出行需特殊身份或许可",
        "- 各坊之间有严格的等级划分，平民与权贵居住区域分明",
    ]
    # 穿越设定
    if "穿越" in keywords:
        lines += [
            "",
            "## 穿越设定",
            "- 穿越方式：灵魂穿越（现代意识进入古代身体，保留前世记忆）",
            "- 原主身份：大理寺底层人员，因性格孤僻被同僚排挤，独自居住",
            "- 记忆融合程度：初期记忆混乱（前世今生记忆交织），随剧情逐步融合",
            "- 穿越契机：主角在现代因意外身亡，灵魂被系统选中穿越到大唐",
            "- 金手指限制：不能直接透露穿越事实，否则系统惩罚",
        ]
    # 案件体系
    if "悬疑" in keywords:
        lines += [
            "",
            "## 案件体系",
            "- 核心案件：长安城系列离奇死亡事件（主线贯穿全文）",
            "- 案件层级：主线大案（贯穿全剧）> 章节案件（3-5章一破）> 线索碎片",
            "- 破案方式：现场勘查 + 人证物证 + 系统辅助（线索提示、逻辑推演）",
            "- 案件特点：每起案件表面独立，实则指向同一个幕后黑手",
        ]
    # 系统设定
    if "系统" in keywords:
        lines += [
            "",
            "## 系统设定",
            f"- 系统名称：{system_name}",
            "- 系统能力/技能：【洞察之眼】（发现隐藏线索）、【逻辑推演】（重组证据链）、【线索扫描】（自动标记可疑物品）",
            "- 升级方式：破案获得经验值，积累到一定程度解锁新技能",
            "- 限制规则：技能有冷却时间，关键线索需主角自行推理而非系统直接告知",
            "- 系统表现形式：虚拟面板，仅主角可见，消息用【】括起",
        ]
    # 历史背景
    if "历史" in keywords:
        lines += [
            "",
            "## 历史背景",
            "- 朝代/时期：唐朝贞观年间（公元627-649年）",
            "- 关键历史事件：贞观之治、玄奘西行（可作为背景元素）",
            "- 社会制度特点：均田制、府兵制、科举制初行",
            "- 大理寺职权：负责审理重大案件，拥有独立司法权",
        ]
    # 都市背景
    if "都市" in keywords:
        lines += [
            "",
            "## 时代背景",
            "- 城市/地点：长安城（世界最大都市，人口百万）",
            "- 社会阶层：皇族 > 权贵官僚 > 士族 > 平民 > 贱民",
            "- 行业背景：东西两市商业繁荣，丝绸之路起点，多元文化交融",
        ]
    lines += [
        "",
        "## 核心设定",
        "- 设定1：系统是穿越伴随产物，与主角的灵魂绑定，不可剥离",
        "- 设定2：越重大的案件经验值越高，但风险也越大",
        "",
        "## 设定禁忌",
        "- 不可自相矛盾",
        "- 不可临时增加设定解决冲突",
    ]
    return "\n".join(lines)


def _content_characters(name: str, genre: str, keywords: set) -> str:
    """生成角色档案（含默认角色名和定位）"""
    lines = [
        f"# 角色档案\n",
        f"## 主角\n",
        f"### 基本信息",
        f"- **姓名**：（待定）",
        f"- **年龄**：约25岁",
        f"- **身份**：大理寺见习捕快（穿越前为现代刑侦专家/警校毕业生）",
        f"- **外貌**：（待定）\n",
        f"### 核心动机",
        f"- **欲望**：找出穿越真相、在大唐活下去、揭露幕后黑手",
        f"- **驱动力**：正义感 + 求生的本能 + 对系统的好奇",
        f"- **底线**：不伤无辜、不滥用系统害人\n",
        f"### 核心缺陷",
        f"- 初来乍到不熟悉古代社会的规则，容易露馅",
        f"- 系统依赖症：过度依赖系统提示，忽略自身判断力",
        f"- 原主遗留的人际关系问题需要处理\n",
        f"### 人物弧线",
        f"- **开局**：穿越后迷茫被动，被案件推着走",
        f"- **结局**：成长为独当一面的神探，理解系统的真正意义",
        f"- **关键转变**：从依赖系统到相信自己的判断\n",
    ]
    if "悬疑" in keywords:
        lines += [
            "### 破案能力",
            "- 专业知识：现代刑侦知识（痕迹分析、逻辑推理），但古代适用性有限",
            "- 经验背景：现代警校/刑侦背景，理论知识丰富但实战经验不足",
            "- 弱点/盲区：不熟悉古代社会的人情世故、权贵规则",
        ]
    if "系统" in keywords:
        lines += [
            "### 系统绑定",
            "- 系统初始等级：Lv.1（初级洞察）",
            "- 核心技能：【洞察之眼】——发现场景中的异常细节",
            "- 成长方向：刑侦专家路线，最终解锁完整的真相推演能力",
        ]
    lines += [
        "",
        "---",
        "",
        "## 主要配角",
        "",
        "### 李薇",
        "- **身份**：大理寺文书/记录官",
        "- **与主角关系**：同事，后成为重要搭档",
        "- **动机**：家族的冤案需要翻案，借此机会接近大理寺核心案件",
        "- **作用**：提供官府内部信息支持，情感线对象",
        "",
        "### 赵铭",
        "- **身份**：长安富商，表面是商会会长",
        "- **与主角关系**：疑似幕后黑手，与主角为敌",
        "- **动机**：操控长安地下势力，谋取更大权力",
        "- **作用**：中前期的主要对手，系列案件的幕后推手之一",
        "",
        "### 大理寺少卿（王直）",
        "- **身份**：大理寺二把手，主角的直属上级",
        "- **与主角关系**：赏识主角才能，给予支持",
        "- **动机**：维护大理寺声誉，破获大案巩固地位",
        "- **作用**：提供庇护和资源，关键时刻出手相助",
        "",
        "---",
        "",
        "## 反派",
        "",
        "### 王世充（幕后黑手）",
        "- **身份**：朝中神秘势力代表，表面身份为朝中官员",
        "- **动机**：利用系列案件清除政敌，动摇朝局",
        "- **威胁等级**：高（最终BOSS级）",
        "- **与主角的冲突根源**：主角的调查威胁到他的布局，必须除掉",
        "",
        "### 神秘刺客",
        "- **身份**：王世充培养的死士",
        "- **动机**：执行暗杀任务，为目标清除障碍",
        "- **威胁等级**：中高",
    ]
    return "\n".join(lines)


def _content_outline(name: str, genre: str, keywords: set, outline: list) -> str:
    """生成大纲（含故事引擎描述和具体章纲）"""
    lines = [
        f"# 大纲\n",
        f"## 故事引擎",
        f"{name}的核心驱动力是「穿越者用现代刑侦思维破解古代悬案，同时揭开自身穿越真相」。",
        f"每3-5章构成一个案件单元，案件之间由暗线串联，逐步指向最终幕后黑手。\n",
        f"### 核心悬念",
        f"- 主线：谁在操控长安城的系列案件？目的是什么？",
        f"- 暗线1：主角穿越的原因是什么？系统是谁制造的？",
        f"- 暗线2：原主身份是否隐藏着秘密？\n",
        f"### 节奏规划",
        f"- 每章必须包含：至少1个新线索 + 1次冲突升级 + 1个章末钩子",
        f"- 每5章必须包含：1次事件高潮 + 1次世界观/情感补充\n",
        f"## 叙事结构",
        f"三幕结构（章节数不设上限，可随剧情自然扩展）\n",
        f"| 幕 | 功能 |",
        f"|---|------|",
        f"| 第一幕：开局 | 引入世界观、主角困境、初始冲突 |",
        f"| 第二幕：发展 | 冲突升级、矛盾深化 |",
        f"| 第三幕：终局 | 推向高潮、解决最终冲突 |",
        f"\n## 章纲（初始规划，后续可扩展）\n",
        f"> 提示：以下为初始章纲骨架，写完当前规划后可用 `extend-outline` 命令添加更多章节。\n",
        f"| 章号 | 章名 | 目标 | 冲突 | 新信息 | 钩子 |",
        f"|------|------|------|------|--------|------|",
    ]
    for ch in outline:
        lines.append(
            f"| {ch['chapter']:03d} | {ch['title']} | {ch['goal']} | {ch['conflict']} | {ch['new_info']} | {ch['hook']} |"
        )
    lines += [
        "",
        "## 写作备忘录",
        "- 每次开写前跑 brief 查看当前状态",
        "- 写完一章后更新角色属性和事件矩阵",
        "- 章纲快用完时提前 extend-outline",
    ]
    return "\n".join(lines)


def _content_research(name: str, genre: str, keywords: set) -> str:
    """生成研究资料（填充具体研究方向）"""
    lines = [
        f"# 研究资料\n",
        f"## 参考资料\n",
    ]
    if "历史" in keywords or "穿越" in keywords:
        lines += [
            "### 唐代制度",
            "- 大唐六典：三省六部制、大理寺职权范围",
            "- 唐代司法程序：报案→勘验→审讯→判决→复核",
            "- 唐代职官体系：九品三十阶",
            "",
            "### 唐代社会",
            "- 长安城布局：皇城、宫城、外郭城、108坊",
            "- 唐代服饰制度：颜色代表身份等级",
            "- 唐代宵禁制度：鼓声为号，闭坊门",
            "- 唐代饮食文化：胡风盛行，面食为主",
            "",
    ]
    if "悬疑" in keywords:
        lines += [
            "### 古代刑侦",
            "- 《洗冤集录》：宋代宋慈著，古代法医学经典（虽时代稍晚但可参考）",
            "- 唐代验尸制度：仵作验尸 + 官府记录",
            "- 古代痕迹检验：脚印、指纹（虽无现代技术但有关注）",
            "- 唐代监狱制度：牢狱分类、刑讯规则",
            "",
            "### 现代刑侦（主角前世知识）",
            "- 犯罪现场保护与勘查流程",
            "- 法医学基础：死亡时间判断、伤型分析",
            "- 物证链管理：证据保管与交接",
            "",
    ]
    if "系统" in keywords:
        lines += [
            "### 系统设定参考",
            "- 游戏化升级系统设计（经验值 → 等级 → 新技能）",
            "- 冷却机制平衡设计",
            "- 系统限制与剧情张力的关系",
            "",
    ]
    lines += [
        "## 考据笔记",
        "",
        "### 需核实的细节",
        "- ",
        "",
        "### 已考据的内容",
        "- ",
        "",
        "## 灵感来源",
        "",
        "### 参考作品",
        "- 《大唐狄公案》：古代探案标杆",
        "- 《少年包青天》：古代探案 + 悬疑节奏",
        "- 番茄平台悬疑探案类爆款书：节奏分析",
        "",
        "### 个人灵感",
        "- ",
    ]
    return "\n".join(lines)


def generate_bible_content(project_root: Path, name: str, genre: str, author: str, initial_estimate: int):
    """根据题材生成完整的 bible 文件内容（字段已填充，非空壳）"""
    keywords = _detect_genre_keywords(genre)
    outline = _chapter_outline(initial_estimate)

    write_md(project_root / "bible" / "00-world-building.md", _content_world_building(name, genre, author, keywords))
    write_md(project_root / "bible" / "01-character-profiles.md", _content_characters(name, genre, keywords))
    write_md(project_root / "bible" / "03-outline.md", _content_outline(name, genre, keywords, outline))
    write_md(project_root / "bible" / "04-research.md", _content_research(name, genre, keywords))

    # style-guide 需要 keywords 和名称, 保持原有逻辑
    narrative = "第三人称有限视角"
    tone = "正剧"
    lang = "简洁"
    if "悬疑" in keywords:
        narrative = "第三人称有限视角（跟随主角）"
        tone = "冷峻悬疑"
        lang = "冷峻、简洁、画面感强"
    if "穿越" in keywords:
        tone += "，古今碰撞带温度"
    if "系统" in keywords:
        lang += "，系统消息用【】括起"
    if "言情" in keywords:
        tone = "细腻情感"
        lang = "细腻、生动、画面感强"
    if "玄幻" in keywords:
        tone = "热血"
        lang = "画面感强、节奏明快"

    sg_lines = [
        f"# 风格指南\n",
        f"## 叙事风格",
        f"- **视角**：{narrative}",
        f"- **基调**：{tone}",
        f"- **语言风格**：{lang}\n",
        f"## 禁用词",
        f"见 CLAUDE.md 中的去AI味指南\n",
        f"## 去AI味要求",
        f"- 程度：严格",
        f"- 重点关注模式：",
        f"  - \"不禁\"\"仿佛\"等高频AI词",
        f"  - 情绪解释（\"他感到\"\"她心中\"）",
        f"  - 弱副词（\"微微\"\"缓缓\"）",
        f"  - 一问一答式对话\n",
        f"## 写作偏好",
        f"- 对话比例：30-40%",
        f"- 段落长度：短段为主，3-5行一段",
        f"- 标点使用：中文标点\n",
        f"## 字数规则",
        f"- 每章 3000-3500 字（全阶段统一）",
        f"- 铁律：一次性写满，绝不事后补字数\n",
        f"## 所在项目",
        f"- **项目名**：{name}",
        f"- **题材**：{genre}",
        f"- **章节**：不设上限，随剧情自然扩展",
    ]
    write_md(project_root / "bible" / "02-style-guide.md", "\n".join(sg_lines))


def create_project(
    name: str,
    genre: str,
    output_dir: str = ".",
    author: str = "",
    chapter_count: int = 20,
    writing_type: str = "medium",
) -> Path:
    """创建新小说项目"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = name.replace(" ", "_")[:20]
    project_dir = Path(output_dir) / f"{timestamp}-{safe_name}"

    # 写入类型配置
    type_config = get_writing_type_config(writing_type) or {}

    # 创建目录结构
    dirs = [
        "bible",
        "state/current",
        "state/template",
        "manuscript",
        "knowledge",
        "gates",
    ]
    for d in dirs:
        ensure_dir(project_dir / d)

    # 生成完整的 bible 文件（不再从空模板复制）
    generate_bible_content(project_dir, name, genre, author, chapter_count)

    # 获取正确的字数限制
    min_words, max_words = 3000, 3500
    if type_config.get("phased") and type_config.get("phases"):
        min_words = type_config["phases"][0]["min"]
        max_words = type_config["phases"][0]["max"]
    elif type_config.get("word_limits"):
        min_words = type_config["word_limits"]["min"]
        max_words = type_config["word_limits"]["max"]

    # 初始化 state
    now = datetime.now().isoformat()
    state_template = {
        "project": {
            "name": name, "genre": genre, "author": author,
            "estimated_chapters": chapter_count, "writing_type": writing_type,
        },
        "progress": {"current_chapter": 0, "completed_chapters": [], "status": "initialized", "synced_up_to_chapter": 0},
        "summary": {"latest_events": [], "pending_foreshadowing": [], "active_conflicts": []},
        "config": {"word_limits": {"min": min_words, "max": max_words}},
        "created_at": now,
        "last_updated": now,
    }
    write_json(project_dir / "state" / "current" / "state.json", state_template)
    write_json(project_dir / "state" / "template" / "state.json", state_template.copy())

    # 初始化 knowledge
    story_graph = {
        "nodes": [],
        "edges": [],
        "version": 1,
        "last_updated": now,
    }
    write_json(project_dir / "knowledge" / "story_graph.json", story_graph)

    event_matrix = {
        "events": [],
        "cooldowns": {
            "conflict_thrill": 2,
            "bond_deepening": 1,
            "faction_building": 2,
            "world_painting": 3,
            "tension_escalation": 2,
        },
        "config": {"min_bond_or_world_every_n": 5},
    }
    write_json(project_dir / "knowledge" / "event_matrix.json", event_matrix)

    write_md(project_dir / "knowledge" / "timeline.md",
             f"# 时间线\n\n项目：{name}\n创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    # gates 占位
    write_md(project_dir / "gates" / ".gitkeep", "")

    print(f"✅ 项目已创建：{project_dir}")
    print(f"   题材：{genre}")
    print(f"   章节：不设上限（初始规划约{chapter_count}章）")
    print(f"   每章字数：{min_words}-{max_words}")
    print(f"   目录结构：")
    for d in dirs:
        print(f"     {project_dir / d}/")
    print(f"   Bible 文件已根据题材生成完整内容。")
    return project_dir


def main():
    parser = argparse.ArgumentParser(description="Novel Master: 初始化新小说项目")
    parser.add_argument("name", help="小说名称")
    parser.add_argument("--genre", "-g", default="未分类", help="小说题材")
    parser.add_argument("--output", "-o", default=".", help="输出目录")
    parser.add_argument("--author", "-a", default="", help="作者名")
    parser.add_argument("--chapters", "-c", type=int, default=0, help="计划章节数（0=使用类型默认值）")
    parser.add_argument("--type", "-t", choices=list(WRITING_TYPES.keys()), default="medium",
                        help="写作类型: short=短篇, medium=中篇, long=长篇, tomato=番茄连载")

    args = parser.parse_args()

    type_config = get_writing_type_config(args.type)
    chapter_count = args.chapters if args.chapters > 0 else type_config["default_chapters"]

    print(f"写作类型: {type_config['label']}")
    print(f"字数范围: {type_config['word_limits']['min']}-{type_config['word_limits']['max']}字/章")
    if type_config.get("phased"):
        print("阶段规则:")
        for phase in type_config["phases"]:
            print(f"  {phase['name']} (第{phase['chapters'][0]}-{phase['chapters'][1]}章): {phase['min']}-{phase['max']}字")

    create_project(
        name=args.name,
        genre=args.genre,
        output_dir=args.output,
        author=args.author,
        chapter_count=chapter_count,
        writing_type=args.type,
    )


if __name__ == "__main__":
    main()
