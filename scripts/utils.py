"""Novel Master: 共享工具模块"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ========== 写作类型配置 ==========

WRITING_TYPES = {
    "short": {
        "label": "短篇",
        "desc": "1万-4万字，适合短故事、参赛",
        "default_chapters": 8,
        "word_limits": {"min": 2000, "max": 4000},
        "phased": False,
    },
    "medium": {
        "label": "中篇",
        "desc": "6万-15万字，适合单主线完整故事",
        "default_chapters": 25,
        "word_limits": {"min": 3000, "max": 5000},
        "phased": False,
    },
    "long": {
        "label": "长篇",
        "desc": "18万-50万字，适合多卷体量",
        "default_chapters": 60,
        "word_limits": {"min": 3000, "max": 5000},
        "phased": False,
    },
    "tomato": {
        "label": "番茄连载",
        "desc": "10万-100万字+，适配番茄平台推荐规则",
        "default_chapters": 50,
        "word_limits": {"min": 3000, "max": 3500},
        "phased": True,
        "phases": [
            {"name": "黄金三章", "chapters": (1, 3), "min": 3000, "max": 3500},
            {"name": "首秀期", "chapters": (4, 10), "min": 3000, "max": 3500},
            {"name": "连载期", "chapters": (11, 9999), "min": 3000, "max": 3500},
        ],
    },
}


def get_writing_type_config(writing_type: str) -> Optional[Dict]:
    """获取写作类型配置"""
    return WRITING_TYPES.get(writing_type)


def get_word_limits_for_chapter(writing_type: str, chapter_num: int) -> Tuple[int, int]:
    """根据写作类型和章节号获取字数限制 (min, max)"""
    config = WRITING_TYPES.get(writing_type)
    if not config:
        return 2000, 5000

    if config.get("phased"):
        for phase in config["phases"]:
            start, end = phase["chapters"]
            if start <= chapter_num <= end:
                return phase["min"], phase["max"]

    limits = config["word_limits"]
    return limits["min"], limits["max"]


def get_phase_name(writing_type: str, chapter_num: int) -> str:
    """获取当前章节所处的阶段名"""
    config = WRITING_TYPES.get(writing_type)
    if not config or not config.get("phased"):
        return ""
    for phase in config["phases"]:
        start, end = phase["chapters"]
        if start <= chapter_num <= end:
            return phase["name"]
    return ""


def get_project_root(project_path: Optional[str] = None) -> Path:
    """获取项目根目录"""
    if project_path:
        return Path(project_path)
    # 从当前目录向上查找
    cwd = Path.cwd()
    for marker in ["bible", "state", "manuscript"]:
        if (cwd / marker).exists():
            return cwd
    return cwd


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_md(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_md(path: Path, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def chapter_number(filename: str) -> int:
    """从文件名提取章节号，如 第001章-xxx.md -> 1"""
    m = re.search(r"(\d+)", filename)
    return int(m.group(1)) if m else 0


def count_chinese_chars(text: str) -> int:
    """统计中文字符数"""
    return len(re.findall(r"[一-鿿]", text))


def get_chapter_files(project_root: Path) -> List[Path]:
    """获取所有正文章节文件（按编号排序）"""
    ms_dir = project_root / "manuscript"
    if not ms_dir.exists():
        return []
    files = sorted(ms_dir.glob("第*.md"))
    return sorted(files, key=lambda f: chapter_number(f.name))


def get_latest_chapter(project_root: Path) -> Optional[Path]:
    """获取最新章节文件"""
    files = get_chapter_files(project_root)
    return files[-1] if files else None


def get_gate_status(project_root: Path, chapter_num: int) -> Optional[Dict]:
    """获取指定章节的门禁检查状态"""
    gate_file = project_root / "gates" / f"第{chapter_num:03d}章-gate.json"
    if gate_file.exists():
        return read_json(gate_file)
    return None


def summary_from_chapter(text: str, max_chars: int = 200) -> str:
    """从章节正文生成摘要"""
    # 移除空行和Markdown标记
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    summary = ""
    for line in lines:
        if len(summary) + len(line) > max_chars:
            break
        summary += line[:50] + "…" if len(line) > 50 else line
    return summary[:max_chars]
