#!/usr/bin/env python3
"""Novel Master: 七猫小说发布 — 基于 Playwright 浏览器表单上传

技术方案：通过 Playwright 打开七猫作家后台的章节编辑页面，
直接填写标题和正文后点击保存。

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
from typing import Dict, Optional

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

WRITER_HOME_URL = "https://zuozhe.qimao.com"
AUTH_STATE_FILENAME = "qimao-auth-state.json"
PUBLISH_STATE_FILENAME = "qimao-publish-state.json"
BOOK_ID = "11901780"  # 用户已有书籍


# ========== Playwright 检测 ==========

def _check_playwright():
    """检测 Playwright 是否可用"""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        print("❌ 未安装 Playwright，七猫发布功能不可用。")
        print("   安装命令：")
        print("     pip install playwright")
        print("     playwright install chromium")
        return False


# ========== 认证管理 ==========

def _get_auth_state_path(project_root: Optional[Path] = None) -> Path:
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
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    launch_args = ["--disable-blink-features=AutomationControlled"]

    if auth_state_path.exists() and auth_state_path.stat().st_size > 10:
        browser = await pw.chromium.launch(headless=False, args=launch_args)
        context = await browser.new_context(
            storage_state=str(auth_state_path),
            viewport={"width": 1280, "height": 800},
        )
    else:
        browser = await pw.chromium.launch(headless=False, args=launch_args)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

    page = await context.new_page()
    return pw, browser, context, page


async def _save_auth_state(context, auth_state_path: Path):
    auth_state_path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(auth_state_path))
    print(f"✅ 认证状态已保存到 {auth_state_path}")


async def _check_logged_in(page) -> bool:
    """检查是否已登录"""
    url = page.url
    if "login" in url:
        return False
    try:
        body_text = await page.inner_text("body")
        if "登录" in body_text and "手机号" in body_text:
            return False
    except Exception:
        pass
    return True


async def _navigate_and_check_login(page) -> bool:
    try:
        await page.goto(WRITER_HOME_URL, timeout=15000)
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    return await _check_logged_in(page)


# ========== 章节解析 ==========

def _parse_chapter_browser(filepath: Path) -> Dict:
    """解析 MD 文件"""
    text = read_md(filepath)
    lines = text.split("\n")

    fn_match = re.search(r"第0*(\d+)章", filepath.name)
    chapter_num = fn_match.group(1) if fn_match else str(chapter_number(filepath.name))

    title_line = lines[0].strip()
    if title_line.startswith("#"):
        title_line = title_line.lstrip("#").strip()
    chapter_name = re.sub(r"^第\d*[零一二三四五六七八九十百千]*章[\s_\-]*", "", title_line).strip()

    body_lines = [l for l in lines[1:] if not l.strip().startswith("#")]
    body = "\n".join(body_lines).strip()

    return {
        "file": str(filepath),
        "chapter_num": chapter_num,
        "chapter_name": chapter_name,
        "body_text": body,
        "word_count": count_chinese_chars(body),
    }


# ========== 子命令实现 ==========

async def cmd_login(args):
    """手机验证码登录七猫作家后台"""
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

        print("\n📱 七猫作家后台需要手机验证码登录")
        print("   请在浏览器中完成登录\n")

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

    chapter_files = get_chapter_files(project_root)
    if not chapter_files:
        print("❌ manuscript/ 下没有章节文件")
        return 1

    if args.chapter:
        chapter_files = [f for f in chapter_files if chapter_number(f.name) == args.chapter]
    else:
        uploaded = set(pub_state.get("uploaded_chapters", {}).keys())
        chapter_files = [f for f in chapter_files if str(chapter_number(f.name)) not in uploaded]

    if not chapter_files:
        print("✅ 没有需要上传的章节（全部已上传）")
        return 0

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

    chapters_to_upload = [_parse_chapter_browser(f) for f in chapter_files]
    print(f"\n📤 准备上传 {len(chapters_to_upload)} 章到草稿箱（book_id: {book_id}）")

    pw, browser, context, page = await _launch_browser(auth_path)

    try:
        if not await _navigate_and_check_login(page):
            print("❌ 登录已过期，请重新登录: python3 qimao_publish.py login")
            return 1

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

        return 0 if fail_count == 0 else 1

    finally:
        await browser.close()
        await pw.stop()


async def _upload_via_browser(page, book_id: str, ch: Dict) -> bool:
    """通过浏览器页面上传单章到草稿箱"""
    try:
        # 1. 导航到新建章节页面
        url = f"https://zuozhe.qimao.com/front/book-upload?id={book_id}"
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # 2. 填写章节标题（先清空再填）
        title_input = page.locator('input[placeholder="请输入章节名称，最多20个字"]')
        await title_input.wait_for(state="visible", timeout=10000)
        await title_input.fill("")
        await title_input.fill("")
        await title_input.fill(ch["chapter_name"])
        await page.wait_for_timeout(500)

        # 3. 填写正文内容（先清空再填）
        content_editor = page.locator('div.q-contenteditable.book.font-size-16.edit-mask')
        await content_editor.wait_for(state="visible", timeout=10000)
        await content_editor.click()
        await page.wait_for_timeout(200)
        # 两次 fill("") 确保清空
        await content_editor.fill("")
        await content_editor.fill("")
        await page.wait_for_timeout(300)
        await page.keyboard.type(ch["body_text"])
        await page.wait_for_timeout(2000)

        # 4. 点击"存为草稿"并等待5秒弹窗确认
        save_btn = page.locator('a:has-text("存为草稿")')
        await save_btn.wait_for(timeout=5000)
        await save_btn.click()

        # 5. 等待弹窗出现，等待倒计时结束（按钮不再是disabled），然后点击
        await page.wait_for_timeout(1000)
        # 弹窗里的按钮文字是"我已阅读并知晓(N)"，倒计时结束后disabled会移除
        read_ack_btn = page.locator('a.qm-btn.important:has-text("我已阅读并知晓")')
        await read_ack_btn.wait_for(state="visible", timeout=10000)
        # 等待按钮不再是disabled（倒计时结束）
        while True:
            disabled = await read_ack_btn.get_attribute("disabled")
            if disabled is None:
                break
            await page.wait_for_timeout(500)
        # 点击确认
        await read_ack_btn.click()
        await page.wait_for_timeout(3000)

        return True

    except Exception as e:
        print(f"⚠️  浏览器上传异常: {e}")
        return False


def cmd_status(args):
    """查看发布状态"""
    project_root = Path(args.project)
    pub_state = _load_publish_state(project_root)

    book_id = pub_state.get("book_id") or BOOK_ID
    uploaded = pub_state.get("uploaded_chapters", {})
    last_updated = pub_state.get("last_updated")

    print(f"\n📊 七猫发布状态")
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

    return 0


# ========== CLI 入口 ==========

def main():
    parser = argparse.ArgumentParser(description="Novel Master: 七猫小说发布")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp_login = subparsers.add_parser("login", help="手机验证码登录七猫作家后台")
    sp_login.add_argument("-p", "--project", help="项目路径（可选）")

    sp_upload = subparsers.add_parser("upload", help="上传章节到草稿箱")
    sp_upload.add_argument("-p", "--project", required=True, help="项目路径")
    sp_upload.add_argument("--book-id", help="七猫书籍 ID")
    sp_upload.add_argument("--chapter", type=int, help="指定单章章节号")
    sp_upload.add_argument("--force", action="store_true", help="跳过门禁检查")

    sp_status = subparsers.add_parser("status", help="查看发布状态")
    sp_status.add_argument("-p", "--project", required=True, help="项目路径")

    args = parser.parse_args()

    cmd_map = {"login": cmd_login, "upload": cmd_upload, "status": cmd_status}

    if args.command in ("login", "upload"):
        exit_code = asyncio.run(cmd_map[args.command](args))
    else:
        exit_code = cmd_map[args.command](args)

    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
