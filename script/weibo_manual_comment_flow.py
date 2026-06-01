#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw


OUTPUT_DIR = Path.home() / "outputs/weibo-comment-shots"
PROFILE_DIR = Path.home() / ".playwright-weibo-profile"

COMMENT_TEXT_SELECTORS = [
    'text={comment_text}',
    'blockquote:has-text("{comment_text}")',
    'div:has-text("{comment_text}")',
    'span:has-text("{comment_text}")',
    'p:has-text("{comment_text}")',
]

COMMENT_ROOT_SELECTORS = [
    '.WB_feed_detail, [data-testid="comment-list"], .woo-box-flex.woo-box-alignCenter.woo-box-justifyBetween',
    '[data-testid="comment-list"]',
    '.WB_feed_detail',
    '.woo-box-flex.woo-box-alignCenter.woo-box-justifyBetween',
    '.woo-box-flex.woo-box-column',
]

COMMENT_PANEL_SELECTORS = [
    '[aria-label="评论"]',
    'article button[title="评论"]',
    'button:has-text("评论")',
    '[role="button"]:has-text("评论")',
    'a:has-text("评论")',
]

COMMENT_SUBMIT_SELECTORS = [
    'button:has-text("发送")',
    '[role="button"]:has-text("发送")',
    'button:has-text("发布")',
    '[role="button"]:has-text("发布")',
    'button:has-text("评论")',
]

LOGIN_MARKER_SELECTORS = [
    'input[name="username"]',
    'input[name="password"]',
    'input[type="password"]',
    '.login-box',
    '.woo-panel-login',
]

LOGGED_IN_COMPOSER_SELECTORS = [
    'textarea',
    '[contenteditable="true"]',
    'div[role="textbox"]',
]

COMMENT_COMPOSER_SELECTORS = [
    '[data-testid="comment-composer"] textarea',
    '[data-testid="comment-composer"] [contenteditable="true"]',
    '.woo-box-item-flex textarea',
    '.woo-box-item-flex [contenteditable="true"]',
    '.comment textarea',
    '.comment [contenteditable="true"]',
    'textarea',
    'div[role="textbox"]',
    'div[contenteditable="plaintext-only"]',
    '[contenteditable="true"]',
]

TIME_SORT_ACTIVE_SELECTORS = [
    '[aria-checked="true"]:has-text("按时间")',
    '[aria-current="true"]:has-text("按时间")',
    '[aria-selected="true"]:has-text("按时间")',
    '.woo-tab-item-main[aria-selected="true"]:has-text("按时间")',
]

PAGE_READY_SELECTORS = [
    'article',
    '[data-testid="comment-list"]',
    '.WB_feed_detail',
    '.woo-box-flex.woo-box-column',
    'textarea',
]


def configure_wslg_env():
    """Make headed Chromium work reliably when launched from non-interactive WSL shells."""
    if not os.environ.get("DISPLAY") and Path("/tmp/.X11-unix/X0").exists():
        os.environ["DISPLAY"] = ":0"
    if not os.environ.get("XDG_RUNTIME_DIR") and Path("/mnt/wslg/runtime-dir").exists():
        os.environ["XDG_RUNTIME_DIR"] = "/mnt/wslg/runtime-dir"
    if not os.environ.get("WAYLAND_DISPLAY") and Path("/mnt/wslg/runtime-dir/wayland-0").exists():
        os.environ["WAYLAND_DISPLAY"] = "wayland-0"
    if not os.environ.get("PULSE_SERVER") and Path("/mnt/wslg/PulseServer").exists():
        os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"


def safe_stem(text: str, limit: int = 48) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return (cleaned or "comment")[:limit]


def emit_evidence_event(event_type: str, payload: dict):
    event = {"type": event_type, **payload}
    print(f"EVIDENCE={json.dumps(event, ensure_ascii=False, sort_keys=True)}", flush=True)


def build_like_evidence(status: str | None, selector: str | None, state: dict | None):
    return {
        "type": "like",
        "status": status,
        "selector": selector,
        "state": state,
    }


def build_submission_evidence(
    submit_selector: str | None,
    wait_result: str | None,
    login_required: bool,
    comment_visible: bool,
):
    return {
        "type": "submission",
        "submit_selector": submit_selector,
        "wait_result": wait_result,
        "login_required": login_required,
        "comment_visible": comment_visible,
    }


def build_final_summary(
    *,
    status: str,
    initial_wait_result: str | None = None,
    submit_wait_result: str | None = None,
    locate_wait_result: str | None = None,
    like_status: str | None = None,
    submission_confirmed: bool | None = None,
    comment_found: bool | None = None,
    login_required: bool | None = None,
    primary_mode: str | None = None,
    final_screenshot: str | None = None,
):
    return {
        "type": "final-summary",
        "status": status,
        "wait": {
            "initial_load": initial_wait_result,
            "after_submit": submit_wait_result,
            "before_locate_comment": locate_wait_result,
        },
        "like_status": like_status,
        "submission_confirmed": submission_confirmed,
        "comment_found": comment_found,
        "login_required": login_required,
        "primary_mode": primary_mode,
        "final_screenshot": final_screenshot,
    }


def emit_final_summary(payload: dict):
    print(f"FINAL_SUMMARY={json.dumps(payload, ensure_ascii=False, sort_keys=True)}", flush=True)


def first_visible_locator(root, selectors: list[str], timeout: int = 3000):
    for selector in selectors:
        locator = root.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            locator.wait_for(state="visible", timeout=timeout)
            return locator, selector
        except Exception:
            continue
    return None, None


def page_requires_login(page) -> bool:
    composer, _ = first_visible_locator(page, LOGGED_IN_COMPOSER_SELECTORS, timeout=1000)
    if composer is not None:
        return False

    marker, _ = first_visible_locator(page, LOGIN_MARKER_SELECTORS, timeout=1000)
    if marker is not None:
        return True

    try:
        login_text = page.get_by_text("登录").first
        if login_text.count() > 0 and login_text.is_visible(timeout=1000):
            return True
    except Exception:
        pass
    return False


def comment_text_selectors(comment_text: str) -> list[str]:
    return [selector.format(comment_text=comment_text) for selector in COMMENT_TEXT_SELECTORS]


def is_liked_state(state: dict | None) -> bool:
    if not state:
        return False
    class_name = (state.get('className') or '').lower()
    count_class = (state.get('countClass') or '').lower()
    title = (state.get('title') or '').strip()
    text = (state.get('text') or '').strip()
    return (
        'woo-like-liked' in count_class
        or 'liked' in class_name
        or title in {'已赞', '取消赞'}
        or text.startswith('已赞')
    )


def choose_highlight_box(text_box: dict | None, expanded_box: dict | None):
    if expanded_box and expanded_box.get('width', 0) > 0 and expanded_box.get('height', 0) > 0:
        return expanded_box
    return text_box


def normalize_crop_box(crop_box: dict, highlight_box: dict):
    x = max(int(crop_box['x']), 0)
    y = max(int(crop_box['y']), 0)
    right = max(int(crop_box['right']), int(highlight_box['right']))
    bottom = max(int(crop_box['bottom']), int(highlight_box['bottom']))
    if right <= x:
        right = max(int(highlight_box['right']), x + max(int(highlight_box.get('width', 1)), 1))
    if bottom <= y:
        bottom = max(int(highlight_box['bottom']), y + max(int(highlight_box.get('height', 1)), 1))
    return {'x': x, 'y': y, 'right': right, 'bottom': bottom}


def ensure_time_sort(page) -> bool:
    try:
        target = page.get_by_text('按时间').first
        if target.count() > 0 and target.is_visible(timeout=1000):
            target.click(timeout=5000)
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(2000)
            active, _ = first_visible_locator(page, TIME_SORT_ACTIVE_SELECTORS, timeout=1000)
            return active is not None
    except Exception:
        return False
    return False


def wait_for_page_ready(
    page,
    context: str,
    readiness_selectors: list[str] | None = None,
    networkidle_timeout: int = 10000,
    selector_timeout: int = 2000,
    fallback_wait_ms: int = 1200,
):
    try:
        page.wait_for_load_state("networkidle", timeout=networkidle_timeout)
        return "networkidle"
    except PlaywrightTimeoutError:
        pass

    selectors = readiness_selectors or PAGE_READY_SELECTORS
    locator, selector = first_visible_locator(page, selectors, timeout=selector_timeout)
    if locator is not None:
        return f"selector:{selector}"

    if hasattr(page, "wait_for_timeout"):
        try:
            page.wait_for_timeout(fallback_wait_ms)
            return "timeout-fallback"
        except Exception:
            pass
    return "no-ready-signal"


def find_comment_locator_in_root(root, comment_text: str):
    candidates = comment_text_selectors(comment_text)
    for selector in candidates:
        locator = root.locator(selector).first
        try:
            if locator.count() > 0 and locator.is_visible(timeout=1500):
                return locator, selector
        except Exception:
            continue
    return None, None


def find_comment_in_comments_root(page, comment_text: str):
    root, _ = first_visible_locator(page, COMMENT_ROOT_SELECTORS, timeout=2000)
    if root is None:
        return None, None
    return find_comment_locator_in_root(root, comment_text)


def open_comment_panel(page):
    locator, selector = first_visible_locator(page, COMMENT_PANEL_SELECTORS)
    if locator is None:
        return None
    locator.click(timeout=3000)
    return selector


def submit_comment(page):
    locator, selector = first_visible_locator(page, COMMENT_SUBMIT_SELECTORS)
    if locator is None:
        return None
    locator.click(timeout=3000)
    return selector


def verify_comment_submission(page, comment_text: str, attempts: int = 4, wait_ms: int = 1200) -> bool:
    for _ in range(attempts):
        if page_requires_login(page):
            return False
        locator, _ = find_comment_in_comments_root(page, comment_text)
        if locator is not None:
            return True
        if hasattr(page, "wait_for_timeout"):
            try:
                page.wait_for_timeout(wait_ms)
            except Exception:
                pass
    return False


def find_comment_locator(page, comment_text: str):
    return find_comment_in_comments_root(page, comment_text)


def draw_red_box(raw_path: Path, boxed_path: Path, box: dict):
    image = Image.open(raw_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    x0 = max(int(box["x"]) - 8, 0)
    y0 = max(int(box["y"]) - 8, 0)
    x1 = min(int(box["x"] + box["width"]) + 8, image.width - 1)
    y1 = min(int(box["y"] + box["height"]) + 8, image.height - 1)
    for offset in range(4):
        draw.rectangle([x0 - offset, y0 - offset, x1 + offset, y1 + offset], outline=(255, 0, 0), width=2)
    image.save(boxed_path)


def locator_document_box(locator, expand_selector: str | None = None):
    js = """
    (el, { expandSelector }) => {
        let target = el;
        if (expandSelector) {
            const expanded = target.closest(expandSelector);
            if (expanded) target = expanded;
        }
        const r = target.getBoundingClientRect();
        return {
            x: r.x + window.scrollX,
            y: r.y + window.scrollY,
            width: r.width,
            height: r.height,
            right: r.right + window.scrollX,
            bottom: r.bottom + window.scrollY,
        };
    }
    """
    return locator.evaluate(js, {"expandSelector": expand_selector})


def first_visible_document_box(page, selectors: list[str]):
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            locator.wait_for(state="visible", timeout=2000)
            return locator_document_box(locator), selector
        except Exception:
            continue
    return None, None


def save_contextual_crop(full_raw_path: Path, focused_raw_path: Path, focused_boxed_path: Path, crop_box: dict, highlight_box: dict):
    image = Image.open(full_raw_path).convert("RGB")
    left = max(int(crop_box["x"]), 0)
    top = max(int(crop_box["y"]), 0)
    right = min(int(crop_box["right"]), image.width)
    bottom = min(int(crop_box["bottom"]), image.height)
    cropped = image.crop((left, top, right, bottom))
    cropped.save(focused_raw_path)

    relative_box = {
        "x": highlight_box["x"] - left,
        "y": highlight_box["y"] - top,
        "width": highlight_box["width"],
        "height": highlight_box["height"],
    }
    draw = ImageDraw.Draw(cropped)
    x0 = max(int(relative_box["x"]) - 8, 0)
    y0 = max(int(relative_box["y"]) - 8, 0)
    x1 = min(int(relative_box["x"] + relative_box["width"]) + 8, cropped.width - 1)
    y1 = min(int(relative_box["y"] + relative_box["height"]) + 8, cropped.height - 1)
    for offset in range(4):
        draw.rectangle([x0 - offset, y0 - offset, x1 + offset, y1 + offset], outline=(255, 0, 0), width=2)
    cropped.save(focused_boxed_path)


def fill_comment_box(page, comment_text: str):
    selectors = COMMENT_COMPOSER_SELECTORS
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            locator.wait_for(state="visible", timeout=3000)
            locator.click(timeout=2000)
            try:
                locator.fill(comment_text, timeout=2000)
            except Exception:
                locator.press("Control+A", timeout=1000)
                locator.type(comment_text, delay=30, timeout=5000)
            return locator, selector
        except Exception:
            continue
    return None, None


def click_comment_button(page):
    return open_comment_panel(page)


def ensure_post_liked(page):
    selectors = [
        'article button[title="赞"]',
        'article .woo-like-main',
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            locator.wait_for(state="visible", timeout=3000)
            state = locator.evaluate(
                """
                el => ({
                    className: el.className || '',
                    countClass: el.querySelector('.woo-like-count')?.className || '',
                    title: el.getAttribute('title') || '',
                    text: (el.innerText || el.textContent || '').trim(),
                })
                """
            )
            if is_liked_state(state):
                return 'already-liked', selector, state
            locator.click(timeout=3000)
            page.wait_for_timeout(1500)
            after = locator.evaluate(
                """
                el => ({
                    className: el.className || '',
                    countClass: el.querySelector('.woo-like-count')?.className || '',
                    title: el.getAttribute('title') || '',
                    text: (el.innerText || el.textContent || '').trim(),
                })
                """
            )
            if is_liked_state(after):
                return 'liked-now', selector, after
            return 'clicked-unknown', selector, after
        except Exception:
            continue
    return None, None, None


def main():
    parser = argparse.ArgumentParser(description="Manual-assisted Weibo comment screenshot workflow")
    parser.add_argument("--url", required=True, help="Target Weibo URL")
    parser.add_argument("--comment", required=True, help="Comment text to locate and box")
    parser.add_argument("--headless", action="store_true", help="Run headless (not recommended for manual login)")
    parser.add_argument("--submit", action="store_true", help="Try to auto-fill and auto-submit the comment")
    parser.add_argument("--like", action="store_true", help="Ensure the target Weibo post is liked before capture/submission")
    parser.add_argument("--capture-only", action="store_true", help="Skip submission and just locate an existing matching comment for screenshot evidence")
    parser.add_argument("--full-page-primary", action="store_true", help="Use full-page boxed screenshot as the primary output instead of the focused contextual crop")
    args = parser.parse_args()

    configure_wslg_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(args.comment)
    raw_path = OUTPUT_DIR / f"{stem}_raw.png"
    boxed_path = OUTPUT_DIR / f"{stem}_boxed.png"
    focused_raw_path = OUTPUT_DIR / f"{stem}_context_raw.png"
    focused_boxed_path = OUTPUT_DIR / f"{stem}_context_boxed.png"

    print("[0/5] GUI env:", {
        "DISPLAY": os.environ.get("DISPLAY"),
        "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY"),
        "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR"),
    }, flush=True)
    print("[1/5] Launching Chromium with persistent profile...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=args.headless,
            viewport={"width": 1440, "height": 1800},
        )
        page = browser.new_page()
        page.set_default_timeout(15000)
        initial_wait_result = None
        submit_wait_result = None
        locate_wait_result = None
        like_status = None
        login_required_after_submit = None
        comment_visible_after_submit = None
        comment_found = False
        primary_mode = None
        final_screenshot = None

        print(f"[2/5] Opening: {args.url}", flush=True)
        page.goto(args.url, wait_until="domcontentloaded")
        initial_wait_result = wait_for_page_ready(page, context="initial-load", readiness_selectors=PAGE_READY_SELECTORS, networkidle_timeout=10000)
        emit_evidence_event("wait", {"context": "initial-load", "result": initial_wait_result})

        if page_requires_login(page):
            emit_final_summary(
                build_final_summary(
                    status="login-required-initial",
                    initial_wait_result=initial_wait_result,
                    login_required=True,
                )
            )
            print("检测到当前页面处于登录/风控态，请先完成登录后再继续。", flush=True)
            browser.close()
            sys.exit(6)

        if args.like:
            print("[2.5/5] Ensuring the post is liked...", flush=True)
            like_status, like_selector, like_state = ensure_post_liked(page)
            emit_evidence_event("like", build_like_evidence(like_status, like_selector, like_state))
            if like_status is None:
                print("未自动找到点赞按钮。", flush=True)
            else:
                print(f"LIKE_STATUS={like_status}", flush=True)
                print(f"LIKE_SELECTOR={like_selector}", flush=True)
                print(f"LIKE_STATE={like_state}", flush=True)

        if args.submit:
            print("[3/5] Trying to auto-fill and auto-submit the comment...", flush=True)
            button_selector = open_comment_panel(page)
            if button_selector:
                print(f"已先打开评论面板，按钮选择器: {button_selector}", flush=True)
                page.wait_for_timeout(1500)
            else:
                print("未自动找到“评论”按钮，直接尝试定位评论输入框。", flush=True)

            box_locator, box_selector = fill_comment_box(page, args.comment)
            if box_locator is None and button_selector is not None:
                page.wait_for_timeout(1500)
                box_locator, box_selector = fill_comment_box(page, args.comment)
            if box_locator is None:
                print("仍未找到评论输入框。", flush=True)
                browser.close()
                sys.exit(4)
            print(f"已填入评论，输入框选择器: {box_selector}", flush=True)

            submit_selector = submit_comment(page)
            if not submit_selector:
                print("未自动找到可提交的发送/发布按钮。", flush=True)
                browser.close()
                sys.exit(5)
            print(f"已点击提交按钮，按钮选择器: {submit_selector}", flush=True)
            submit_wait_result = wait_for_page_ready(
                page,
                context="after-submit",
                readiness_selectors=COMMENT_ROOT_SELECTORS + LOGGED_IN_COMPOSER_SELECTORS,
                networkidle_timeout=6000,
                fallback_wait_ms=1500,
            )
            emit_evidence_event("wait", {"context": "after-submit", "result": submit_wait_result})
            login_required_after_submit = page_requires_login(page)
            comment_visible_after_submit = verify_comment_submission(page, args.comment)
            emit_evidence_event(
                "submission",
                build_submission_evidence(
                    submit_selector=submit_selector,
                    wait_result=submit_wait_result,
                    login_required=login_required_after_submit,
                    comment_visible=comment_visible_after_submit,
                ),
            )
            if login_required_after_submit:
                emit_final_summary(
                    build_final_summary(
                        status="login-required-after-submit",
                        initial_wait_result=initial_wait_result,
                        submit_wait_result=submit_wait_result,
                        like_status=like_status,
                        submission_confirmed=False,
                        comment_found=False,
                        login_required=True,
                    )
                )
                print("提交后页面进入登录/风控态，未确认评论成功发布。", flush=True)
                browser.close()
                sys.exit(7)
            if not comment_visible_after_submit:
                print("未确认评论成功出现在评论区，停止后续截图以避免假阳性。", flush=True)
                page.screenshot(path=str(raw_path), full_page=True)
                final_screenshot = str(raw_path.resolve())
                print(f"RAW_SCREENSHOT={raw_path.resolve()}", flush=True)
                print("BOXED_SCREENSHOT=NOT_FOUND", flush=True)
                emit_final_summary(
                    build_final_summary(
                        status="submission-not-confirmed",
                        initial_wait_result=initial_wait_result,
                        submit_wait_result=submit_wait_result,
                        like_status=like_status,
                        submission_confirmed=False,
                        comment_found=False,
                        login_required=False,
                        primary_mode="full_page",
                        final_screenshot=final_screenshot,
                    )
                )
                browser.close()
                sys.exit(8)
        elif args.capture_only:
            print("[3/5] Capture-only mode: skipping comment submission and locating existing comment only...", flush=True)
        else:
            print("\n请在打开的浏览器里手动完成以下动作：", flush=True)
            print("  1) 登录微博", flush=True)
            print("  2) 如需点赞请手动点赞", flush=True)
            print(f"  3) 手动发布这条评论：{args.comment}", flush=True)
            input("\n完成后回到当前终端，按 Enter 继续截图与标注... ")

        print("[4/5] Trying to locate your comment on the page...", flush=True)
        page.bring_to_front()
        locate_wait_result = wait_for_page_ready(
            page,
            context="before-locate-comment",
            readiness_selectors=COMMENT_ROOT_SELECTORS + ['article'],
            networkidle_timeout=5000,
            fallback_wait_ms=1000,
        )
        emit_evidence_event("wait", {"context": "before-locate-comment", "result": locate_wait_result})
        if ensure_time_sort(page):
            print("已切换评论排序到：按时间", flush=True)
        else:
            print("未能切换到“按时间”，将按当前排序继续查找。", flush=True)

        if page_requires_login(page):
            emit_final_summary(
                build_final_summary(
                    status="login-required-before-capture",
                    initial_wait_result=initial_wait_result,
                    submit_wait_result=submit_wait_result,
                    locate_wait_result=locate_wait_result,
                    like_status=like_status,
                    submission_confirmed=comment_visible_after_submit,
                    comment_found=False,
                    login_required=True,
                )
            )
            print("截图前检测到页面回到了登录/风控态，停止以避免误框。", flush=True)
            browser.close()
            sys.exit(9)

        locator, selector = find_comment_locator(page, args.comment)
        if locator is None:
            print("未能直接定位到评论文本。正在截全页原图，供后续人工检查。", flush=True)
            page.screenshot(path=str(raw_path), full_page=True)
            final_screenshot = str(raw_path.resolve())
            print(f"RAW_SCREENSHOT={raw_path.resolve()}", flush=True)
            print("BOXED_SCREENSHOT=NOT_FOUND", flush=True)
            emit_final_summary(
                build_final_summary(
                    status="comment-not-found",
                    initial_wait_result=initial_wait_result,
                    submit_wait_result=submit_wait_result,
                    locate_wait_result=locate_wait_result,
                    like_status=like_status,
                    submission_confirmed=comment_visible_after_submit,
                    comment_found=False,
                    login_required=False,
                    primary_mode="full_page",
                    final_screenshot=final_screenshot,
                )
            )
            browser.close()
            sys.exit(2)

        comment_found = True
        print(f"找到评论，使用选择器: {selector}", flush=True)
        try:
            locator.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass

        text_box = locator_document_box(locator)
        if not text_box:
            print("评论已找到，但无法读取其坐标。仅输出原始截图。", flush=True)
            page.screenshot(path=str(raw_path), full_page=True)
            final_screenshot = str(raw_path.resolve())
            print(f"RAW_SCREENSHOT={raw_path.resolve()}", flush=True)
            print("BOXED_SCREENSHOT=NOT_FOUND", flush=True)
            emit_final_summary(
                build_final_summary(
                    status="comment-found-no-box",
                    initial_wait_result=initial_wait_result,
                    submit_wait_result=submit_wait_result,
                    locate_wait_result=locate_wait_result,
                    like_status=like_status,
                    submission_confirmed=comment_visible_after_submit,
                    comment_found=True,
                    login_required=False,
                    primary_mode="full_page",
                    final_screenshot=final_screenshot,
                )
            )
            browser.close()
            sys.exit(3)
        highlight_box = choose_highlight_box(
            text_box,
            locator_document_box(locator, '.item1, .wbpro-list, .woo-box-flex.item1in, .con1, .text')
        )
        if not highlight_box:
            highlight_box = text_box

        article_box, article_selector = first_visible_document_box(page, ['article', '.wbpro-feed-content'])
        if not article_box:
            article_box = {
                'x': max(highlight_box['x'] - 40, 0),
                'y': max(highlight_box['y'] - 500, 0),
                'right': highlight_box['right'] + 40,
                'bottom': highlight_box['bottom'] + 80,
            }
            article_selector = 'fallback'

        crop_box = normalize_crop_box({
            'x': max(min(article_box['x'], highlight_box['x']) - 20, 0),
            'y': max(article_box['y'] - 20, 0),
            'right': max(article_box['right'], highlight_box['right']) + 20,
            'bottom': highlight_box['bottom'] + 80,
        }, highlight_box)

        print("[5/5] Saving full-page screenshot...", flush=True)
        page.screenshot(path=str(raw_path), full_page=True)

        print("[5/5+] Drawing red rectangle around the detected comment...", flush=True)
        draw_red_box(raw_path, boxed_path, text_box)
        save_contextual_crop(raw_path, focused_raw_path, focused_boxed_path, crop_box, highlight_box)

        primary_raw_path = raw_path if args.full_page_primary else focused_raw_path
        primary_boxed_path = boxed_path if args.full_page_primary else focused_boxed_path
        primary_mode = "full_page" if args.full_page_primary else "contextual"
        final_screenshot = str(primary_boxed_path.resolve())

        print(f"POST_SELECTOR={article_selector}", flush=True)
        print(f"PRIMARY_MODE={primary_mode}", flush=True)
        print(f"RAW_SCREENSHOT={primary_raw_path.resolve()}", flush=True)
        print(f"BOXED_SCREENSHOT={primary_boxed_path.resolve()}", flush=True)
        print(f"FULL_RAW_SCREENSHOT={raw_path.resolve()}", flush=True)
        print(f"FULL_BOXED_SCREENSHOT={boxed_path.resolve()}", flush=True)
        print(f"CONTEXT_RAW_SCREENSHOT={focused_raw_path.resolve()}", flush=True)
        print(f"CONTEXT_BOXED_SCREENSHOT={focused_boxed_path.resolve()}", flush=True)
        emit_final_summary(
            build_final_summary(
                status="ok",
                initial_wait_result=initial_wait_result,
                submit_wait_result=submit_wait_result,
                locate_wait_result=locate_wait_result,
                like_status=like_status,
                submission_confirmed=comment_visible_after_submit,
                comment_found=comment_found,
                login_required=False,
                primary_mode=primary_mode,
                final_screenshot=final_screenshot,
            )
        )
        print("[5/5++] Closing page/context while preserving login state in the persistent profile...", flush=True)
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
