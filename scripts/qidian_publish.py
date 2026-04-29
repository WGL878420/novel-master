#!/usr/bin/env python3
"""Novel Master: 起点小说发布 — 基于 Playwright 浏览器表单上传

技术方案：通过 Playwright 打开起点作家后台的章节编辑页面，
直接填写章号、标题和正文后点击保存。

子命令:
    login   手机验证码登录
    upload  上传章节到草稿箱
    status  查看发布状态
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from utils import (
        read_json, write_json, read_md, get_chapter_files,
        chapter_number, count_chinese_chars,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from utils import (
        read_json, write_json, read_md, get_chapter_files,
        chapter_number, count_chinese_chars,
    )

# ========== 常量 ==========

WRITER_HOME_URL = "https://write.qq.com"
AUTH_STATE_FILENAME = "qidian-auth-state.json"
PUBLISH_STATE_FILENAME = "qidian-publish-state.json"
BOOK_ID = "35730802204107809"  # 用户已有书籍


# ========== Playwright 检测 ==========

def _check_playwright():
    """检测 Playwright 是否可用，给出友好提示"""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        print("❌ 未安装 Playwright，起点发布功能不可用。")
        print("   安装命令：")
        print("     pip install playwright")
        print("     playwright install chromium")
        print("")
        print("   安装后重新运行此命令即可。")
        return False


# ========== 认证管理 ==========

def _get_auth_state_path(project_root: Optional[Path] = None) -> Path:
    """认证状态文件路径：优先项目级，其次全局"""
    if project_root:
        p = project_root / "state" / AUTH_STATE_FILENAME
        if p.exists():
            return p
    global_dir = Path.home() / ".novel-master"
    global_dir.mkdir(parents=True, exist_ok=True)
    return global_dir / AUTH_STATE_FILENAME


def _get_publish_state_path(project_root: Path) -> Path:
    return project_root / "state" / PUBLISH_STATE_FILENAME


def _load_publish_state(project_root: Path) -> Dict:
    path = _get_publish_state_path(project_root)
    if path.exists():
        return read_json(path)
    return {"uploaded_chapters": {}, "book_id": None, "last_updated": None}


def _save_publish_state(project_root: Path, state: Dict):
    state["last_updated"] = datetime.now().isoformat()
    write_json(_get_publish_state_path(project_root), state)


# ========== 浏览器管理 ==========

async def _launch_browser(auth_state_path: Path):
    """启动浏览器，如有认证状态则加载"""
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    launch_args = ["--disable-blink-features=AutomationControlled"]

    if auth_state_path.exists() and auth_state_path.stat().st_size > 10:
        browser = await pw.chromium.launch(headless=False, args=launch_args)
        context = await browser.new_context(
            storage_state=str(auth_state_path),
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        )
    else:
        browser = await pw.chromium.launch(headless=False, args=launch_args)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

    page = await context.new_page()
    return pw, browser, context, page


async def _save_auth_state(context, auth_state_path: Path):
    """保存浏览器认证状态"""
    auth_state_path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(auth_state_path))
    print(f"✅ 认证状态已保存到 {auth_state_path}")


async def _check_logged_in(page) -> bool:
    """检查当前页面是否已登录（不导航，仅检查当前页）"""
    url = page.url
    if "login" in url or "passport" in url:
        return False

    try:
        body_text = await page.inner_text("body")
    except Exception:
        return False

    # 起点未登录提示
    not_logged_in_indicators = ["登录", "手机号", "验证码", "请登录"]
    for indicator in not_logged_in_indicators:
        if indicator in body_text:
            return False

    # 起点已登录状态
    logged_in_indicators = ["作品管理", "创建作品", "我的作品", "作者中心", "退出"]
    for indicator in logged_in_indicators:
        if indicator in body_text:
            return True

    return False


async def _navigate_and_check_login(page) -> bool:
    """导航到作家后台并检查登录状态"""
    try:
        await page.goto(WRITER_HOME_URL, timeout=15000)
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    return await _check_logged_in(page)


# ========== 章节解析 ==========

def _parse_chapter_file(filepath: Path) -> Dict:
    """解析章节 Markdown 文件，提取标题和正文"""
    text = read_md(filepath)
    lines = text.split("\n")

    chapter_num = chapter_number(filepath.name)

    title_match = re.match(r"第\d+章[_\s-]*(.+?)\.md$", filepath.name)
    display_title = title_match.group(1).strip() if title_match else filepath.stem

    body_lines = []
    skip_first_heading = True
    for line in lines:
        if skip_first_heading and line.strip().startswith("#"):
            skip_first_heading = False
            continue
        skip_first_heading = False
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    word_count = count_chinese_chars(body)

    return {
        "file": str(filepath),
        "chapter_num": chapter_num,
        "title": f"第{chapter_num}章 {display_title}",
        "display_title": display_title,
        "body": body,
        "word_count": word_count,
    }


def _parse_chapter_browser(filepath: Path) -> Dict:
    """解析 MD 文件，返回浏览器上传所需的信息"""
    text = read_md(filepath)
    lines = text.split("\n")

    # 章号从文件名取：第009章-魏府.md → 9
    fn_match = re.search(r"第0*(\d+)章", filepath.name)
    chapter_num = fn_match.group(1) if fn_match else str(chapter_number(filepath.name))

    # 标题从第一行取：'# 第九章 魏府' → '魏府'
    title_line = lines[0].strip()
    if title_line.startswith("#"):
        title_line = title_line.lstrip("#").strip()
    chapter_name = re.sub(r"^第\d*[零一二三四五六七八九十百千]*章[\s_\-]*", "", title_line).strip()

    # 正文（跳过标题行）
    body_lines = [l for l in lines[1:] if not l.strip().startswith("#")]
    body = "\n".join(body_lines).strip()

    # 转 HTML
    paragraphs = []
    for line in body.split("\n"):
        line = line.strip()
        if line:
            escaped = line.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
            paragraphs.append(f"<p>{escaped}</p>")
    body_html = "".join(paragraphs)

    return {
        "file": str(filepath),
        "chapter_num": chapter_num,
        "chapter_name": chapter_name,
        "body_html": body_html,
        "word_count": count_chinese_chars(body),
    }


# ========== 子命令实现 ==========

async def cmd_login(args):
    """手机验证码登录起点作家后台"""
    if not _check_playwright():
        return 1

    auth_path = _get_auth_state_path(
        Path(args.project) if hasattr(args, "project") and args.project else None
    )

    pw, browser, context, page = await _launch_browser(auth_path)

    try:
        if await _navigate_and_check_login(page):
            print("✅ 已经是登录状态，无需重新登录")
            await _save_auth_state(context, auth_path)
            return 0

        print("\n📱 起点作家后台需要手机验证码登录")
        print("   请在浏览器中完成登录\n")

        # 等待用户操作 - 检测登录成功
        for i in range(90):
            await asyncio.sleep(2)
            if await _check_logged_in(page):
                print("✅ 登录成功！")
                await _save_auth_state(context, auth_path)
                return 0
            if (i + 1) % 15 == 0:
                remaining = 180 - (i + 1) * 2
                print(f"   ⏳ 等待登录中... 剩余 {remaining} 秒")

        print("❌ 登录超时（180秒），请重试")
        return 1

    finally:
        await browser.close()
        await pw.stop()


async def _upload_via_browser(page, book_id: str, ch: Dict) -> bool:
    """通过浏览器页面表单上传单章到草稿箱"""
    try:
        # 起点新建章节草稿页面
        url = f"https://write.qq.com/portal/booknovels/chaptertmp/CBID/{book_id}/addType/1.html"
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(3000)

        # 填标题
        title_input = page.locator('input[name="title"], input[placeholder*="标题"], input#chapterTitle')
        await title_input.wait_for(timeout=10000)
        await title_input.fill(f"第{ch['chapter_num']}章 {ch['chapter_name']}")

        # 填正文（可能有多重选择器）
        content_selectors = [
            'textarea[name="content"]',
            'textarea#content',
            'textarea[name="chapterContent"]',
            'div[contenteditable="true"]',
            'div.editor-content',
        ]
        content_filled = False
        for sel in content_selectors:
            try:
                content_area = page.locator(sel)
                if await content_area.count() > 0:
                    await content_area.fill(ch["body_html"])
                    content_filled = True
                    break
            except Exception:
                continue

        if not content_filled:
            # 尝试直接用 JavaScript 注入内容
            await page.evaluate("""(html) => {
                // 尝试找到富文本编辑器
                const editors = document.querySelectorAll('div[contenteditable="true"], div.fr-element, div.ProseMirror');
                if (editors.length > 0) {
                    editors[0].innerHTML = html;
                    editors[0].dispatchEvent(new Event('input', { bubbles: true }));
                } else {
                    // 尝试找textarea
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        if (ta.name.includes('content') || ta.id.includes('content')) {
                            ta.value = html;
                            ta.dispatchEvent(new Event('change', { bubbles: true }));
                            break;
                        }
                    }
                }
            }""", ch["body_html"])

        # 点击保存按钮
        save_selectors = [
            'button:has-text("保存")',
            'button:has-text("存草稿")',
            'button:has-text("发布")',
            'a:has-text("保存")',
            'button[type="submit"]',
        ]
        for sel in save_selectors:
            try:
                save_btn = page.locator(sel)
                if await save_btn.count() > 0:
                    await save_btn.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        return True
    except Exception as e:
        print(f"⚠️  浏览器上传异常: {e}")
        return False


async def cmd_upload(args):
    """上传章节到草稿箱"""
    if not _check_playwright():
        return 1

    project_root = Path(args.project)
    if not (project_root / "manuscript").exists():
        print(f"❌ 项目路径无效（找不到 manuscript/）: {project_root}")
        return 1

    auth_path = _get_auth_state_path(project_root)
    pub_state = _load_publish_state(project_root)

    book_id = args.book_id or pub_state.get("book_id") or BOOK_ID

    # 解析章节文件
    chapter_files = get_chapter_files(project_root)
    if not chapter_files:
        print("❌ manuscript/ 下没有章节文件")
        return 1

    if args.chapter:
        chapter_files = [f for f in chapter_files if chapter_number(f.name) == args.chapter]
    else:
        # 默认：上传所有未上传的
        uploaded = set(pub_state.get("uploaded_chapters", {}).keys())
        chapter_files = [f for f in chapter_files if str(chapter_number(f.name)) not in uploaded]

    if not chapter_files:
        print("✅ 没有需要上传的章节（全部已上传）")
        return 0

    # 检查门禁状态（仅在非 --force 时）
    if not args.force:
        valid_files = []
        for f in chapter_files:
            cnum = chapter_number(f.name)
            gate_file = project_root / "gates" / f"第{cnum:03d}章-gate.json"
            if gate_file.exists():
                gate = read_json(gate_file)
                if gate.get("overall") == "pass":
                    valid_files.append(f)
                else:
                    print(f"⏭️  跳过第{cnum:03d}章（门禁未通过）")
            else:
                print(f"⏭️  跳过第{cnum:03d}章（无门禁记录）")
        chapter_files = valid_files

    if not chapter_files:
        print("❌ 没有通过门禁的章节可上传。用 --force 可跳过门禁检查")
        return 1

    # 解析章节内容
    chapters_to_upload = []
    for f in chapter_files:
        parsed = _parse_chapter_browser(f)
        chapters_to_upload.append(parsed)

    print(f"\n📤 准备上传 {len(chapters_to_upload)} 章到草稿箱（book_id: {book_id}）")

    pw, browser, context, page = await _launch_browser(auth_path)

    try:
        if not await _navigate_and_check_login(page):
            print("❌ 登录已过期，请重新登录: python3 qidian_publish.py login")
            return 1

        # 刷新认证状态
        await _save_auth_state(context, auth_path)

        success_count = 0
        fail_count = 0

        for ch in chapters_to_upload:
            print(f"  📝 上传第{ch['chapter_num']}章: {ch['chapter_name']} ({ch['word_count']}字)...", end=" ")

            ok = await _upload_via_browser(page, book_id, ch)

            if ok:
                print("✅")
                success_count += 1
                pub_state["uploaded_chapters"][str(ch["chapter_num"])] = {
                    "title": f"第{ch['chapter_num']}章 {ch['chapter_name']}",
                    "word_count": ch["word_count"],
                    "mode": "draft",
                    "uploaded_at": datetime.now().isoformat(),
                    "file": ch["file"],
                }
            else:
                print("❌")
                fail_count += 1

            await asyncio.sleep(1)

        _save_publish_state(project_root, pub_state)

        print(f"\n{'=' * 40}")
        print(f"上传完成: ✅ {success_count} 成功, ❌ {fail_count} 失败")
        if success_count > 0:
            print(f"请登录起点作家后台检查草稿箱: {WRITER_HOME_URL}")

        return 0 if fail_count == 0 else 1

    finally:
        await browser.close()
        await pw.stop()


def cmd_status(args):
    """查看发布状态"""
    project_root = Path(args.project)
    pub_state = _load_publish_state(project_root)

    book_id = pub_state.get("book_id") or BOOK_ID
    uploaded = pub_state.get("uploaded_chapters", {})
    last_updated = pub_state.get("last_updated")

    print(f"\n📊 起点发布状态")
    print(f"   项目: {project_root}")
    print(f"   Book ID: {book_id}")
    print(f"   最后更新: {last_updated or '无'}")
    print(f"   已上传章节: {len(uploaded)}")

    if uploaded:
        print(f"\n   {'章节':<10} {'标题':<25} {'字数':<8} {'上传时间'}")
        print(f"   {'-' * 65}")
        for ch_num in sorted(uploaded.keys(), key=int):
            info = uploaded[ch_num]
            print(f"   第{int(ch_num):03d}章   {info.get('title', '?'):<25} "
                  f"{info.get('word_count', 0):<8} {info.get('uploaded_at', '?')[:16]}")

    # 检查 manuscript 中有多少章未上传
    chapter_files = get_chapter_files(project_root)
    uploaded_nums = set(uploaded.keys())
    not_uploaded = [f for f in chapter_files if str(chapter_number(f.name)) not in uploaded_nums]
    if not_uploaded:
        print(f"\n   📋 待上传: {len(not_uploaded)} 章")
        for f in not_uploaded[:5]:
            print(f"      - {f.name}")
        if len(not_uploaded) > 5:
            print(f"      ... 还有 {len(not_uploaded) - 5} 章")

    return 0


# ========== CLI 入口 ==========

def main():
    parser = argparse.ArgumentParser(
        description="Novel Master: 起点小说发布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 qidian_publish.py login                         # 登录
  python3 qidian_publish.py upload -p ./my-novel --chapter 5
  python3 qidian_publish.py upload -p ./my-novel --chapter 1 --force
  python3 qidian_publish.py status -p ./my-novel
""",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # login
    sp_login = subparsers.add_parser("login", help="手机验证码登录起点作家后台")
    sp_login.add_argument("-p", "--project", help="项目路径（可选）")

    # upload
    sp_upload = subparsers.add_parser("upload", help="上传章节到草稿箱")
    sp_upload.add_argument("-p", "--project", required=True, help="项目路径")
    sp_upload.add_argument("--book-id", help="起点书籍 ID（不传则用默认或从状态读取）")
    sp_upload.add_argument("--chapter", type=int, help="指定单章章节号")
    sp_upload.add_argument("--force", action="store_true",
                           help="跳过门禁检查，强制上传")

    # status
    sp_status = subparsers.add_parser("status", help="查看发布状态")
    sp_status.add_argument("-p", "--project", required=True, help="项目路径")

    args = parser.parse_args()

    cmd_map = {
        "login": cmd_login,
        "upload": cmd_upload,
        "status": cmd_status,
    }

    if args.command in ("login", "upload"):
        exit_code = asyncio.run(cmd_map[args.command](args))
    else:
        exit_code = cmd_map[args.command](args)

    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
