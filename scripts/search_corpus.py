#!/usr/bin/env python3
"""Novel Master: 语料库检索

适配自 Tomsawyerhu/Chinese-WebNovel-Skill 的检索脚本。
在本地语料库中搜索结构摘录，支持按标签、类型、关键词检索。

语料库结构：
  corpus/
    articles/          # 原文
      A001.md
    analysis/          # 分析结果
      article_profiles.csv
      excerpts.csv
      imitation_index.md
      stats.json
"""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def list_tags() -> List[str]:
    """列出所有可用标签"""
    excerpts_file = CORPUS_DIR / "analysis" / "excerpts.csv"
    if not excerpts_file.exists():
        return []
    tags = set()
    with open(excerpts_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tag_str = row.get("tag", "")
            for t in tag_str.split("|"):
                t = t.strip()
                if t:
                    tags.add(t)
    return sorted(tags)


def list_types() -> List[str]:
    """列出所有摘录类型"""
    excerpts_file = CORPUS_DIR / "analysis" / "excerpts.csv"
    if not excerpts_file.exists():
        return ["开头钩子", "主角亮相", "高张力对白", "结尾余韵"]
    types = set()
    with open(excerpts_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row.get("type", "").strip()
            if t:
                types.add(t)
    return sorted(types)


def search_by_type(excerpt_type: str, tag: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """按类型和标签搜索"""
    excerpts_file = CORPUS_DIR / "analysis" / "excerpts.csv"
    results = []
    if not excerpts_file.exists():
        return results

    with open(excerpts_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("type", "").strip() != excerpt_type:
                continue
            if tag and tag not in row.get("tag", ""):
                continue
            results.append({
                "article": row.get("article", ""),
                "type": row.get("type", ""),
                "tag": row.get("tag", ""),
                "content": row.get("content", ""),
                "note": row.get("note", ""),
            })
            if len(results) >= limit:
                break
    return results


def search_by_keyword(keyword: str, limit: int = 10) -> List[Dict]:
    """按关键词全文搜索"""
    results = []

    # 搜索摘录
    excerpts_file = CORPUS_DIR / "analysis" / "excerpts.csv"
    if excerpts_file.exists():
        with open(excerpts_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                content = row.get("content", "")
                if keyword in content:
                    results.append({
                        "source": "excerpt",
                        "article": row.get("article", ""),
                        "type": row.get("type", ""),
                        "tag": row.get("tag", ""),
                        "content": content[:200],
                    })
                    if len(results) >= limit:
                        break

    # 如果摘录不够，搜索原文目录
    if len(results) < limit:
        articles_dir = CORPUS_DIR / "articles"
        if articles_dir.exists():
            for f in sorted(articles_dir.glob("*.md"))[:limit]:
                text = f.read_text(encoding="utf-8")
                if keyword in text:
                    # 找关键词所在段落
                    for line in text.split("\n"):
                        if keyword in line:
                            results.append({
                                "source": "article",
                                "article": f.stem,
                                "content": line.strip()[:200],
                            })
                            if len(results) >= limit:
                                break

    return results[:limit]


def list_articles() -> List[Dict]:
    """列出语料库中的文章"""
    profiles_file = CORPUS_DIR / "analysis" / "article_profiles.csv"
    results = []
    if profiles_file.exists():
        with open(profiles_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                results.append(row)
    else:
        # fallback: 列出原文目录
        articles_dir = CORPUS_DIR / "articles"
        if articles_dir.exists():
            for f in sorted(articles_dir.glob("*.md")):
                results.append({"id": f.stem, "title": f.stem})
    return results


def get_stats() -> Dict:
    """获取语料库统计"""
    stats_file = CORPUS_DIR / "analysis" / "stats.json"
    if stats_file.exists():
        return json.loads(stats_file.read_text(encoding="utf-8"))
    return {"articles": len(list_articles()), "status": "stats未生成，请先运行蒸馏流程"}


def print_results(results: List[Dict], format: str = "simple"):
    """打印搜索结果"""
    if not results:
        print("无匹配结果")
        return

    for i, r in enumerate(results, 1):
        if format == "simple":
            print(f"\n--- 结果 {i} ---")
            print(f"  文章: {r.get('article', '?')}")
            print(f"  类型: {r.get('type', '-')}")
            if r.get("tag"):
                print(f"  标签: {r['tag']}")
            print(f"  内容: {r.get('content', '')[:150]}")
        elif format == "full":
            print(f"\n{'='*50}")
            print(f"结果 {i}")
            print(f"{'='*50}")
            for k, v in r.items():
                print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="Novel Master: 语料库检索")
    parser.add_argument("action", choices=["list-tags", "list-types", "list-articles",
                                           "search-type", "search-keyword", "stats"],
                       help="操作")
    parser.add_argument("--type", help="摘录类型")
    parser.add_argument("--tag", help="标签")
    parser.add_argument("--keyword", help="关键词")
    parser.add_argument("--limit", type=int, default=5, help="返回数量")
    parser.add_argument("--format", choices=["simple", "full"], default="simple")

    args = parser.parse_args()

    if args.action == "list-tags":
        tags = list_tags()
        if tags:
            print("可用标签：")
            for t in tags:
                print(f"  - {t}")
        else:
            print("语料库为空或未构建，请先添加语料")

    elif args.action == "list-types":
        types = list_types()
        if types:
            print("摘录类型：")
            for t in types:
                print(f"  - {t}")
        else:
            print("默认类型：开头钩子 / 主角亮相 / 高张力对白 / 结尾余韵")

    elif args.action == "list-articles":
        articles = list_articles()
        if articles:
            print(f"语料库文章 ({len(articles)}):")
            for a in articles:
                print(f"  [{a.get('id', '?')}] {a.get('title', a.get('id', '?'))}")
        else:
            print("语料库为空")

    elif args.action == "search-type":
        if not args.type:
            print("❌ search-type 需要 --type 参数")
            return
        results = search_by_type(args.type, args.tag, args.limit)
        print(f"搜索类型「{args.type}」" + (f" + 标签「{args.tag}」" if args.tag else ""))
        print_results(results, args.format)

    elif args.action == "search-keyword":
        if not args.keyword:
            print("❌ search-keyword 需要 --keyword 参数")
            return
        results = search_by_keyword(args.keyword, args.limit)
        print(f"搜索关键词「{args.keyword}」")
        print_results(results, args.format)

    elif args.action == "stats":
        stats = get_stats()
        print(f"语料库统计：")
        for k, v in stats.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
