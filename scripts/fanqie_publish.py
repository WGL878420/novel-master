#!/usr/bin/env python3
"""Novel Master: 番茄小说发布 — 基于 Playwright 浏览器表单上传

技术方案：通过 Playwright 打开番茄作家后台的章节编辑页面，
直接填写章号、标题和正文后点击保存。比 HTTP API 方式更稳定，
不依赖可能变更的后端接口。

子命令:
    setup     首次配置（安装 Playwright + 登录保存会话）
    login     单独登录（刷新过期的会话）
    list-books 列出作家后台已有书籍
    create-book 创建新书
    upload    上传章节到草稿箱（通过浏览器页面表单）
    status    查看发布状态
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

WRITER_HOME_URL = "https://fanqienovel.com/main/writer/?enter_from=author_zone"
AUTH_STATE_FILENAME = "fanqie-auth-state.json"
PUBLISH_STATE_FILENAME = "fanqie-publish-state.json"

API_BASE = "https://fanqienovel.com"
API_COMMON_PARAMS = "aid=2503&app_name=muye_novel"

FANQIE_CATEGORIES = {
    "男频": {
        "玄幻": 1, "奇幻": 2, "武侠": 3, "仙侠": 4,
        "都市": 5, "历史": 7, "军事": 8, "游戏": 9,
        "竞技": 10, "科幻": 11, "灵异": 12, "二次元": 13,
        "末世": 21,
    },
    "女频": {
        "古代言情": 14, "现代言情": 15, "幻想言情": 16,
        "青春校园": 19, "悬疑推理": 20,
    },
}

DAILY_CHAR_LIMIT = 50000


# ========== Playwright 检测 ==========

def _check_playwright():
    """检测 Playwright 是否可用，给出友好提示"""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        print("❌ 未安装 Playwright，番茄发布功能不可用。")
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

    login_indicators = ["扫码登录", "手机号登录", "验证码登录"]
    for indicator in login_indicators:
        if indicator in body_text:
            return False

    logged_in_indicators = ["章节管理", "创建作品", "我的作品", "作品管理"]
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


# ========== FanqieClient: 页面内 fetch 调 API ==========

class FanqieClient:
    """通过 Playwright 页面上下文执行 fetch 调用番茄 API，
    借浏览器的 Cookie 和指纹绕过反爬"""

    def __init__(self, page):
        self.page = page

    async def _fetch(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """在页面 JS 上下文中执行 fetch"""
        url = f"{API_BASE}{path}"
        if "?" in url:
            url += f"&{API_COMMON_PARAMS}"
        else:
            url += f"?{API_COMMON_PARAMS}"

        if method.upper() == "GET":
            js = f"""
            async () => {{
                const resp = await fetch("{url}", {{
                    method: "GET",
                    credentials: "include",
                }});
                return await resp.json();
            }}
            """
        else:
            body_parts = []
            if data:
                for k, v in data.items():
                    body_parts.append(
                        f"encodeURIComponent('{k}') + '=' + encodeURIComponent('{v}')"
                    )
            body_expr = " + '&' + ".join(body_parts) if body_parts else "''"

            js = f"""
            async () => {{
                const body = {body_expr};
                const resp = await fetch("{url}", {{
                    method: "POST",
                    credentials: "include",
                    headers: {{"Content-Type": "application/x-www-form-urlencoded"}},
                    body: body,
                }});
                return await resp.json();
            }}
            """
        try:
            result = await self.page.evaluate(js)
            return result
        except Exception as e:
            return {"code": -1, "message": str(e)}

    async def get_book_list(self) -> List[Dict]:
        """获取作家后台书籍列表"""
        resp = await self._fetch("GET", "/api/author/homepage/book_list/v0/")
        if resp.get("code") == 0:
            return resp.get("data", {}).get("book_list", [])
        print(f"⚠️  获取书籍列表失败: {resp.get('message', '未知错误')}")
        return []

    async def create_book(self, title: str, genre: str, synopsis: str,
                          channel: str = "男频") -> Optional[str]:
        """创建新书，返回 book_id"""
        categories = FANQIE_CATEGORIES.get(channel, {})
        category_id = categories.get(genre)
        if not category_id:
            available = ", ".join(categories.keys())
            print(f"❌ 不支持的分类 '{genre}'，{channel}可用分类: {available}")
            return None

        if len(synopsis) < 50:
            synopsis = synopsis + "。" * (50 - len(synopsis))

        data = {
            "book_name": title,
            "abstract": synopsis,
            "category_id": str(category_id),
            "creation_type": "0",
        }
        resp = await self._fetch("POST", "/api/author/book/create/v0/", data)
        if resp.get("code") == 0:
            book_id = resp.get("data", {}).get("book_id")
            print(f"✅ 创建成功，book_id: {book_id}")
            return str(book_id)
        print(f"❌ 创建失败: {resp.get('message', '未知错误')}")
        return None

    async def save_draft(self, book_id: str, title: str, content_html: str,
                         chapter_serial: int) -> bool:
        """保存章节到草稿箱"""
        data = {
            "book_id": book_id,
            "title": title,
            "content": content_html,
            "chapter_serial": str(chapter_serial),
        }
        resp = await self._fetch("POST", "/api/author/article/new_article/", data)
        if resp.get("code") == 0:
            return True

        # 如果 new_article 失败，尝试 cover_article（更新已有草稿）
        resp2 = await self._fetch("POST", "/api/author/article/cover_article/", data)
        if resp2.get("code") == 0:
            return True

        print(f"⚠️  保存草稿失败: {resp.get('message', '')} / {resp2.get('message', '')}")
        return False


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


def _text_to_html(text: str) -> str:
    """正文转 HTML（按行拆成 <p> 标签），番茄 API 要求 HTML 格式"""
    paragraphs = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            paragraphs.append(f"<p>{line}</p>")
    return "".join(paragraphs)


# ========== 子命令实现 ==========

async def cmd_setup(args):
    """首次配置：检查环境 + 登录"""
    if not _check_playwright():
        return 1

    print("=" * 50)
    print("番茄小说发布 — 首次配置")
    print("=" * 50)

    # 检查 chromium
    print("\n📦 检查 Chromium 浏览器...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"⚠️  Chromium 安装可能有问题: {result.stderr[:200]}")
    else:
        print("✅ Chromium 就绪")

    # 登录
    print("\n🔑 开始登录番茄作家后台...")
    return await cmd_login(args)


async def cmd_login(args):
    """登录番茄作家后台，保存会话"""
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

        print("\n📱 请在浏览器中完成登录（扫码 / 手机号 / 密码均可）")
        print("   登录成功后会自动检测，无需手动操作。")
        print("   超时时间：180秒\n")

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


async def cmd_list_books(args):
    """列出作家后台书籍"""
    if not _check_playwright():
        return 1

    auth_path = _get_auth_state_path(
        Path(args.project) if hasattr(args, "project") and args.project else None
    )

    if not auth_path.exists():
        print("❌ 未找到登录状态，请先运行: python3 fanqie_publish.py setup")
        return 1

    pw, browser, context, page = await _launch_browser(auth_path)

    try:
        if not await _navigate_and_check_login(page):
            print("❌ 登录已过期，请重新登录: python3 fanqie_publish.py login")
            return 1

        client = FanqieClient(page)
        books = await client.get_book_list()

        if not books:
            print("📭 还没有创建过书籍")
            return 0

        print(f"\n📚 书籍列表（共 {len(books)} 本）\n")
        print(f"{'Book ID':<20} {'书名':<30} {'状态':<10} {'字数'}")
        print("-" * 75)
        for book in books:
            book_id = book.get("book_id", "?")
            name = book.get("book_name", "?")
            status_map = {0: "连载中", 1: "已完结", 2: "暂停"}
            status = status_map.get(book.get("creation_status", -1), "未知")
            word_count = book.get("word_count", 0)
            print(f"{book_id:<20} {name:<30} {status:<10} {word_count}字")

        return 0

    finally:
        await browser.close()
        await pw.stop()


async def cmd_create_book(args):
    """创建新书"""
    if not _check_playwright():
        return 1

    auth_path = _get_auth_state_path(
        Path(args.project) if hasattr(args, "project") and args.project else None
    )

    pw, browser, context, page = await _launch_browser(auth_path)

    try:
        if not await _navigate_and_check_login(page):
            print("❌ 登录已过期，请重新登录")
            return 1

        client = FanqieClient(page)
        book_id = await client.create_book(
            title=args.title,
            genre=args.genre,
            synopsis=args.synopsis,
            channel=args.channel,
        )

        if book_id and hasattr(args, "project") and args.project:
            project_root = Path(args.project)
            pub_state = _load_publish_state(project_root)
            pub_state["book_id"] = book_id
            _save_publish_state(project_root, pub_state)
            print(f"📝 book_id 已保存到项目发布状态")

        return 0 if book_id else 1

    finally:
        await browser.close()
        await pw.stop()


async def _upload_via_browser(page, book_id: str, ch: Dict) -> bool:
    """通过浏览器页面表单上传单章到草稿箱"""
    try:
        url = f"https://fanqienovel.com/main/writer/{book_id}/publish/?enter_from=newchapter"
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(5000)

        # 填章号（第 [N] 章）
        num_input = page.locator("span.left-input input")
        await num_input.wait_for(timeout=10000)
        await num_input.fill(str(ch["chapter_num"]))

        # 填标题
        title_input = page.locator('input[placeholder*="标题"]')
        await title_input.wait_for(timeout=5000)
        await title_input.fill(ch["chapter_name"])

        # 填正文（ProseMirror 编辑器）
        await page.evaluate("""(html) => {
            const editor = document.querySelector('.ProseMirror');
            if (editor) {
                editor.innerHTML = html;
                editor.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }""", ch["body_html"])

        # 点击存草稿
        save_btn = page.locator('button:has-text("存草稿")')
        await save_btn.wait_for(timeout=5000)
        await save_btn.click()
        await page.wait_for_timeout(5000)
        return True
    except Exception as e:
        print(f"⚠️  浏览器上传异常: {e}")
        return False


async def cmd_upload(args):
    """上传章节到草稿箱（浏览器表单方式）"""
    if not _check_playwright():
        return 1

    project_root = Path(args.project)
    if not (project_root / "manuscript").exists():
        print(f"❌ 项目路径无效（找不到 manuscript/）: {project_root}")
        return 1

    auth_path = _get_auth_state_path(project_root)
    pub_state = _load_publish_state(project_root)

    book_id = args.book_id or pub_state.get("book_id")
    if not book_id:
        print("❌ 未指定 book_id。请先运行 create-book 或用 --book-id 指定")
        return 1

    # 解析章节范围
    chapter_files = get_chapter_files(project_root)
    if not chapter_files:
        print("❌ manuscript/ 下没有章节文件")
        return 1

    if args.range:
        match = re.match(r"(\d+)-(\d+)", args.range)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            chapter_files = [f for f in chapter_files if start <= chapter_number(f.name) <= end]
        else:
            print(f"❌ 无效的范围格式 '{args.range}'，应为 '1-10'")
            return 1
    elif args.chapter:
        chapter_files = [f for f in chapter_files if chapter_number(f.name) == args.chapter]
    else:
        # 默认：上传所有未上传的已通过门禁的章节
        uploaded = set(pub_state.get("uploaded_chapters", {}).keys())
        chapter_files = [f for f in chapter_files if str(chapter_number(f.name)) not in uploaded]

    if not chapter_files:
        print("✅ 没有需要上传的章节（全部已上传或范围内无文件）")
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

    # 计算字数，检查日限
    total_chars = 0
    chapters_to_upload = []
    for f in chapter_files:
        parsed = _parse_chapter_browser(f)
        total_chars += parsed["word_count"]
        if total_chars > DAILY_CHAR_LIMIT:
            print(f"⚠️  累计字数 {total_chars} 超过日限 {DAILY_CHAR_LIMIT}，截止到第{parsed['chapter_num']}章")
            break
        chapters_to_upload.append(parsed)

    print(f"\n📤 准备上传 {len(chapters_to_upload)} 章到草稿箱（book_id: {book_id}）")
    print(f"   总字数: {total_chars}")

    pw, browser, context, page = await _launch_browser(auth_path)

    try:
        if not await _navigate_and_check_login(page):
            print("❌ 登录已过期，请重新登录: python3 fanqie_publish.py login")
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
            print(f"请登录番茄作家后台检查草稿箱: https://fanqienovel.com/main/writer/")

        return 0 if fail_count == 0 else 1

    finally:
        await browser.close()
        await pw.stop()


async def cmd_status(args):
    """查看发布状态"""
    project_root = Path(args.project)
    pub_state = _load_publish_state(project_root)

    book_id = pub_state.get("book_id")
    uploaded = pub_state.get("uploaded_chapters", {})
    last_updated = pub_state.get("last_updated")

    print(f"\n📊 番茄发布状态")
    print(f"   项目: {project_root}")
    print(f"   Book ID: {book_id or '未绑定'}")
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
        description="Novel Master: 番茄小说发布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 fanqie_publish.py setup                          # 首次配置
  python3 fanqie_publish.py login                          # 登录
  python3 fanqie_publish.py list-books                     # 列出书籍
  python3 fanqie_publish.py create-book -t "书名" -g 玄幻 -s "简介..."
  python3 fanqie_publish.py upload -p ./my-novel --chapter 5
  python3 fanqie_publish.py upload -p ./my-novel --range 1-10
  python3 fanqie_publish.py status -p ./my-novel
""",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup
    sp_setup = subparsers.add_parser("setup", help="首次配置（安装 Chromium + 登录）")
    sp_setup.add_argument("-p", "--project", help="项目路径（可选）")

    # login
    sp_login = subparsers.add_parser("login", help="登录番茄作家后台")
    sp_login.add_argument("-p", "--project", help="项目路径（可选）")

    # list-books
    sp_list = subparsers.add_parser("list-books", help="列出书籍")
    sp_list.add_argument("-p", "--project", help="项目路径（可选）")

    # create-book
    sp_create = subparsers.add_parser("create-book", help="创建新书")
    sp_create.add_argument("-t", "--title", required=True, help="书名")
    sp_create.add_argument("-g", "--genre", required=True, help="分类（如：玄幻、都市、现代言情）")
    sp_create.add_argument("-s", "--synopsis", required=True, help="简介（≥50字）")
    sp_create.add_argument("--channel", default="男频", choices=["男频", "女频"], help="频道")
    sp_create.add_argument("-p", "--project", help="项目路径（可选，自动绑定 book_id）")

    # upload
    sp_upload = subparsers.add_parser("upload", help="上传章节到草稿箱")
    sp_upload.add_argument("-p", "--project", required=True, help="项目路径")
    sp_upload.add_argument("--book-id", help="番茄书籍 ID（不传则从项目状态读取）")
    sp_upload.add_argument("--chapter", type=int, help="指定单章章节号")
    sp_upload.add_argument("--range", help="章节范围（如 1-10）")
    sp_upload.add_argument("--force", action="store_true",
                           help="跳过门禁检查，强制上传")

    # status
    sp_status = subparsers.add_parser("status", help="查看发布状态")
    sp_status.add_argument("-p", "--project", required=True, help="项目路径")

    args = parser.parse_args()

    cmd_map = {
        "setup": cmd_setup,
        "login": cmd_login,
        "list-books": cmd_list_books,
        "create-book": cmd_create_book,
        "upload": cmd_upload,
        "status": cmd_status,
    }

    exit_code = asyncio.run(cmd_map[args.command](args))
    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
