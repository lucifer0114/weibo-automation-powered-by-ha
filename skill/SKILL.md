---
name: weibo-comment-evidence
description: "Use when posting or verifying a Weibo comment via Playwright and you need a proof screenshot in the standardized format: post body + partial comments + red box around the user's own comment."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [weibo, playwright, screenshot, evidence, social-media]
    related_skills: [systematic-debugging]
---

# Weibo Comment Evidence Workflow

## Overview

This workflow standardizes Weibo comment automation, auto-like, and evidence capture.

The required proof format is:
- include the original Weibo post body
- include only part of the comments section
- highlight the user's own comment with a red box
- default the user-facing deliverable to the contextual boxed screenshot
- do **not** use a long full-page screenshot as the primary deliverable or send raw screenshots unless explicitly requested

Critical correctness rule:
- after opening the URL, verify the visible post text/hashtags/author match the requested link before posting anything
- do not trust the URL alone if the browser context looks stale, has navigated to a visitor/login page, or appears to have landed on a different post
- if the content does not match, re-open and re-check the page text before liking/commenting/capturing
- after posting, do not treat a matching sentence anywhere in the page body as proof of success; verify the comment appears as a new item in the comment list under the current account, preferably with a fresh timestamp / fresh sort order
- do not count a whole-page same-text hit as proof of success; the same sentence may already exist in an older comment, another user's comment, or the still-filled composer. Prefer pre-submit vs post-submit comparison plus account/timestamp/newest-position confirmation.
- on dense or high-duplication threads, prefer a shorter and more distinctive comment; if the page already contains many near-duplicate praise comments, a common sentence can be hard to attribute and should not be reused as evidence of success
- if `comments/create` returns `400` but the live body later shows a similar phrase, treat that as a recoverable verification problem: re-open, switch to `按时间`, and confirm the newest item by author + timestamp before deciding the submit really landed

User preference note:
- This user expects a screenshot every time after commenting on Weibo.
- This user prefers the boxed/contextual screenshot, not raw or full-page images.
- When the user sends a Weibo URL, treat it as a request for the full three-step workflow: like, comment, screenshot.

Operational behavior:
- always attempt to ensure the original Weibo post is liked before posting or capturing evidence unless the user explicitly says not to like it
- always post the requested comment
- always capture and return evidence after the comment is posted
- do **not** introduce Browserbase / Browse.sh as the default execution backend for this workflow unless the user explicitly asks to experiment with it; this skill is optimized around the local Playwright + persistent-profile path, and backend churn is usually the wrong fix for comment verification / evidence quality problems
- if the user wants to preserve the current behavior before reliability fixes, create an isolated snapshot repository containing only the Weibo skill assets and script (for example `SKILL.md`, `references/`, and `weibo_manual_comment_flow.py`) rather than committing unrelated changes from the broader `hermes-agent` worktree
- if login blocks progress, first obtain a *visible* QR-code login screenshot and return it to the user so they can scan it; do not send an empty page or a non-QR visitor page as login evidence
- if clicking `去验证` opens a new tab, inspect `ctx.pages` (or equivalent page list) before assuming the verification did nothing; the active page may still be the original post tab while the captcha lives in a separate tab
- if a browser snapshot looks empty but the page may still render a QR/login card, use a visual check before concluding the login page is unusable
- after QR scan, re-check the live page state rather than assuming the post page is ready immediately
- before any like / comment / capture step, explicitly verify the page is still a real post page under the expected account state, not a visitor/login page, QR/SMS auth surface, or abnormal-frequency verification panel.
- if `--capture-only` returns `BOXED_SCREENSHOT=NOT_FOUND`, treat it as a recoverable evidence-matching problem: first retry `--submit --like --headless` on the same URL/comment before doing manual reconstruction
- if the page definitely contains the comment in the DOM but locator text matching fails, switch to a DOM probe (`document.querySelectorAll('*')` / `innerText` scan) to recover the exact node and its bounding box, then crop from the full-page raw screenshot around that anchor
- keep separate logic for opening/expanding the comment area versus submitting the filled comment. A broad `评论` locator reused for both steps is too fragile on Weibo pages and can create false submit success.
- when matching a posted comment for evidence, search inside verified comment-list / comment-card regions first and exclude editable composer areas; avoid whole-page `.first` matches that can lock onto the composer or unrelated duplicate text.
- if the script still cannot match the comment text, use the raw screenshot for visual diagnosis by slicing it into vertical bands and building a contact sheet, then narrow the likely comment region with vision before retrying
- when reconstructing evidence manually, prefer a contextual crop that preserves the post body, the comment composer, and only the relevant portion of the thread; avoid crops that show only the interaction bar or only the target comment
- do not trust a stale `browser_snapshot()` alone after a background run; re-open the URL or use a fresh page check to confirm the live state
- if a helper/navigation path unexpectedly lands on `Sina Visitor System`, verify with a fresh persistent-context page before concluding that login is lost; the main browser helper can be more aggressive than the seeded profile
- if any step is still blocked, report exactly which step failed and why, rather than silently stopping
- if the page shows the abnormal-frequency banner after a submit attempt, stop retrying the same submit path in that session and switch to verification / re-auth handling instead of assuming the comment will eventually go through
- if a comment already exists elsewhere in the page body or in older comments, do not use it as proof of a new submission; require a fresh comment item under the current account, ideally after switching to `按时间` and checking author + timestamp
- after finishing, close the page/context while preserving login state in the persistent profile to reduce memory use

Headless comment-composer pitfall:
- Some Weibo pages expose the composer immediately, while others only reveal it after clicking the visible `评论` button. In headless automation, try `textarea[placeholder="发布你的评论"]` first; if it is absent or hidden, click `评论`, wait briefly, then retry the textarea.
- If the helper says it cannot find the composer but `body.innerText` / DOM inspection shows the textarea exists, bypass the helper and target `textarea[placeholder="发布你的评论"]` directly; the button may be present but visually disabled while still clickable.
- If the page body already proves the target post is correct and the composer exists, do not spend time chasing the helper’s locator path—switch to direct DOM interaction and verify by the new comment appearing in `按时间` order under the current account.
- if the helper says it cannot find the composer but `body.innerText`/DOM inspection shows the textarea exists, bypass the helper and target `textarea[placeholder="发布你的评论"]` directly; the button may be present but visually disabled while still clickable.
- if the textarea fills successfully but the submit button still keeps a `disabled` class, do **not** assume submission is blocked. On this page family, a forced click on the visible `评论` button (`click(force=True)`) can still submit successfully; verify the new comment appears under the current account after sorting by `按时间`.
- on some video posts, the page can show a player/modal UI while the comment composer is still present in the DOM; if the helper misses the composer, inspect the live DOM for the textarea and submit button instead of assuming the post is unusable.
- `textarea[placeholder="发布你的评论"]` first; if it is absent or hidden, click `评论`, wait briefly, then retry the textarea.
- If the textarea exists but `wait_for(state="visible")` stalls, do not assume the composer is absent: scroll a bit more and/or click the visible `评论` control to expand the composer, then retry.
- If the first fill attempt fails, retry after the click + short wait before giving up.
- After filling, the submit button may still look disabled; on some pages `button:has-text("评论")` still posts successfully when clicked with `force=True`.
- Do not rely on `input()` pauses for manual recovery in headless runs; they will raise `EOFError` in non-interactive shells. Use an automatic retry path.
- If a comment seems to submit but disappears on reload, do not treat that as final failure until you have re-opened the page, switched to `按时间`, and re-checked the live list; capture-only can still find the fresh comment once the comment tree settles.

- if `--capture-only` returns `BOXED_SCREENSHOT=NOT_FOUND` even though the comment was just submitted, do not assume the post failed. Re-open the live page, switch to `按时间`, and verify via `body.innerText` or a fresh DOM scan that includes the current account name and the recent timestamp.
- prefer exact/normalized text checks against `body.innerText` over raw `querySelectorAll('*')` string hits; Weibo comment rendering can wrap text in nested nodes and the exact node search can miss a real comment.
- if exact locators return 0 but the page body clearly contains the comment after a sort/scroll change, treat that as a viewport-state issue and continue with a fresh body scan + scroll rather than assuming the comment is missing
- Prefer `body.innerText` confirmation after submit on pages with nested video players / overlays, because the new comment may be present even when locator matching is brittle.
- For manual proof screenshots, crop to the comment region and keep the author + timestamp visible when possible; a visible comment box without the new comment is not enough as evidence.
- If the comment box is visible but the submit button is disabled, that is often a transient composer state rather than a failure; filling the textarea can enable submission.

- See also:
- `references/session-2026-05-09-headless-comment-box.md`
- `references/session-2026-05-19-direct-dom-composer-fallback.md`

Login recovery notes:
- See `references/session-2026-05-09-headless-comment-box.md` for the session pattern where `browser_snapshot()` briefly returned empty after QR scan and the script still recovered.
- See `references/qr-login-capture-checklist.md` for the preferred way to verify a QR page before sending it to the user.
- If QR refresh controls are absent or stale, re-navigation is the reliable refresh path.
- If the visible page and the requested URL disagree, re-check the page text/hashtags/author with `browser_console` before posting anything.
- If `browser_snapshot()` is empty but `browser_console` or `browser_vision` can still see the target post, treat the page state as stale/mismatched and re-navigate rather than assuming the login flow failed.
- After a QR scan or any login transition, re-verify the live page state with a fresh snapshot and page text extraction before liking/commenting.
- See `references/qr-refresh-and-state-check.md` for the newer recovery pattern: snapshot can be empty, QR refresh controls may be absent, and re-navigation is the reliable refresh path.
- See `references/abnormal-behavior-verification-flow.md` for the risk-lock branch where the page loads normally but interaction is blocked by `你的账号异常行为频率较高...`; in that case, opening `登录/注册` reveals the verification panel.

- If the QR code is expired or the user prefers SMS verification, switch to `验证码登录`, then fill `手机号`, click `获取验证码`, and wait for the user to provide the received code.
- If a ref becomes stale after a transition, refresh with a new `browser_snapshot()` or use `browser_console` to discover the live element text before clicking.
- When the post page renders but `评论`/`点赞` remain disabled and the abnormal-frequency message is present, treat this as action restriction rather than expired login; do not keep retrying submit in the same session.
- See `references/session-2026-05-09-qr-recovery-and-comment-box.md` for the concrete recovery pattern from this session: empty snapshot after scan, vision/console verification, then click-评论 fallback.
- See `references/session-2026-05-10-captcha-tab-and-drag-verification.md` for the separate-tab verification pattern after clicking `去验证`.

User-specific delivery defaults:
User-specific delivery defaults:
- when a comment is posted, always return the proof screenshot in the same response
- prefer the contextual boxed screenshot (`*_context_boxed.png`) as the primary artifact
- keep the evidence crop tight and unambiguous; avoid marginal or loosely boxed screenshots that only “roughly” cover the target comment
- the proof screenshot must include both the original post body and the relevant comment area; do not deliver a comment-only crop unless the user explicitly asks for it
- if the user later says a post was not liked, correct it by liking first and then re-capturing the screenshot
- if the target comment is not visible as an exact text hit, do not reuse a guessed crop; re-open, switch to `按时间`, and verify the live DOM/body text again before cropping
- preferred fast path (accepted by user): like first, submit the comment, then generate one tight contextual evidence screenshot containing both正文和评论; if that image is already clear enough, deliver it directly without extra proof iterations
- if the contextual crop is readable, keep it as the primary deliverable; use a full-page boxed screenshot only as a secondary/debug artifact or when the contextual crop is too tight, blurry, or ambiguous
- only do a second pass when the first boxed contextual image is visibly too loose, cropped poorly, ambiguous, or missing正文/评论中的任一部分

If a posted comment is off-topic or the user asks for a different voice, re-read the post text and replace the comment with a corrected version before capturing evidence. See `references/comment-tone-and-rollback.md` for the rollback + tone ladder.

The implementation in this environment is the script:
- `/home/aimashi/spikes/weibo_manual_comment_flow.py`

- See also:
- `references/pre-fix-snapshot-repo.md` — how to preserve the current Weibo automation state in a clean standalone GitHub repo before risky fixes/refactors
- `references/session-pitfalls.md`
- `references/login-wall-recovery.md`
- `references/session-2026-05-19-headless-submit-recovery.md`
- `references/session-2026-05-19-weibo-video-comment-recovery.md`
- `references/session-2026-05-09-qr-recovery-and-comment-box.md`
- `references/session-2026-05-10-captcha-tab-and-drag-verification.md`
- `references/session-2026-05-10-fast-path-timing.md`
- `references/session-2026-05-10-manual-dom-boxing.md`
- `references/session-2026-05-10-qesq-login-and-comment-recovery.md`
- `references/session-2026-05-11-headless-comment-find-and-evidence-choice.md`
- `references/session-2026-05-19-manual-submit-fallback.md`
- `references/session-2026-05-19-qfl4gddvx-comment-recovery.md`
- `references/session-2026-05-19-qfl4gddvx-follow-and-composite.md`
- `references/static-review-2026-06-02-reliability-risks.md` — condensed static review of false-success, locator-scope, login-state, and screenshot-boxing risks in the local Weibo evidence script

It uses:
- persistent Playwright profile: `/home/aimashi/.playwright-weibo-profile`
- output directory: `/home/aimashi/outputs/weibo-comment-shots`
- selector / rollback notes: `references/selectors-and-rollback.md`
- user workflow notes: `references/user-workflow-notes.md`
- login-wall recovery notes: `references/login-wall-recovery.md`
- QR/comment recovery notes: `references/session-2026-05-09-qr-recovery-and-comment-box.md`
- force-submit session note: `references/session-2026-05-19-force-submit-disabled-button.md`
- manual submit fallback note for helper misses: `references/session-2026-05-19-manual-submit-fallback.md`

## When to Use

Use when:
- a Weibo comment needs to be posted automatically after login is already seeded
- an existing comment needs screenshot evidence
- the user wants a repeatable, standardized proof artifact

Do not use when:
- the user has not completed the external QR-code login step at least once in the persistent profile
- you need a brand-new browser/profile instead of the seeded persistent profile
- the requested comment tone is not yet aligned with the post topic; in that case, inspect the post text first and generate a corrected comment before posting

## Standard Output Contract

Primary output must default to the **contextual crop**, not the full-page image.

Primary screenshot requirements:
- post body visible
- only a partial comment area visible
- red box around the user's own comment item
- the primary artifact returned to the user is `BOXED_SCREENSHOT`

User-facing handoff rule:
- after a successful post/capture, include the screenshot as a `MEDIA:/absolute/path` line in the *same* reply
- do not bury the artifact behind extra explanation or make the user ask again
- keep the final handoff brief unless the user explicitly asks for details

Secondary artifacts may still be kept for debugging:
- full-page raw screenshot
- full-page boxed screenshot
- contextual raw screenshot

## Commands

### 1) Capture evidence for an existing comment

```bash
python3 /home/aimashi/spikes/weibo_manual_comment_flow.py \
  --url 'https://weibo.com/<post>' \
  --comment '你的评论文本' \
  --capture-only --headless
```

Expected behavior:
- opens the target post with the persistent profile
- switches sorting to `按时间` when possible
- finds the matching comment text
- saves the contextual crop as the primary screenshot output

### 2) Auto-submit a comment, optionally like first, then capture evidence

Verification rule after submit:
- the new comment must be visible in the comment list under the current account
- if the same sentence already appears elsewhere in the page, do not count that as success
- when duplicates are possible, rely on a fresh comment timestamp / account identity / time-sorted list to disambiguate

Default behavior for this user:
- like the post first when possible
- submit the comment
- capture the contextual boxed screenshot
- return only the boxed/contextual image unless the user asks for more

```bash
python3 /home/aimashi/spikes/weibo_manual_comment_flow.py \
  --url 'https://weibo.com/<post>' \
  --comment '你的评论文本' \
  --submit --like
```

Expected behavior:
- reuses the persistent profile
- if `--like` is set, checks whether the post is already liked and only clicks the like button when needed
- fills the comment box
- clicks the `评论` button
- then switches to `按时间`
- locates the new comment
- saves the contextual crop as the primary screenshot output
- closes the page/context while preserving login state in the persistent profile

Pitfall:
- In some pages the comment textbox is not immediately discoverable in headless mode; if submission stalls, switch to a visible browser session or verify the page has fully loaded before retrying.
- A visible `评论` composer does not guarantee submission success if the account is under an abnormal-frequency action restriction; check for the banner and use verification / re-auth instead of repeated submits.
- if `comments/create` returns `400` with `由于对方的设置，你不能评论哦！`, treat it as a follow/privacy gate first: follow the author if needed, refresh/re-open the composer, then retry a short distinctive comment before changing the text again.
- `networkidle` is only a weak readiness hint on Weibo pages; prefer concrete DOM conditions such as: main post visible, comment area expanded, composer editable, `按时间` switch confirmed, and the newest comment item actually present.
- If you compute screenshot boxes from DOM coordinates and then take a full-page screenshot, re-check layout stability first; lazy rendering and reflow can shift the target and make the red box misleading.

If the user asks for a more casual or ordinary-user tone, prefer a short conversational comment over polished media-copy phrasing. See `references/comment-tone-and-rollback.md`.

### 3) Auto-like + capture-only evidence for an existing comment

```bash
python3 /home/aimashi/spikes/weibo_manual_comment_flow.py \
  --url 'https://weibo.com/<post>' \
  --comment '你的评论文本' \
  --capture-only --like --headless
```

### 4) Force full-page image as the primary artifact

Only use this for debugging.

```bash
python3 /home/aimashi/spikes/weibo_manual_comment_flow.py \
  --url 'https://weibo.com/<post>' \
  --comment '你的评论文本' \
  --capture-only --headless --full-page-primary
```

## Expected Output Fields

The script prints:
- `LIKE_STATUS=...` when `--like` is used
- `PRIMARY_MODE=contextual` by default
- `RAW_SCREENSHOT=...` → primary raw artifact
- `BOXED_SCREENSHOT=...` → primary boxed artifact
- `FULL_RAW_SCREENSHOT=...`
- `FULL_BOXED_SCREENSHOT=...`
- `CONTEXT_RAW_SCREENSHOT=...`
- `CONTEXT_BOXED_SCREENSHOT=...`

Interpretation:
- by default, `RAW_SCREENSHOT` and `BOXED_SCREENSHOT` point to the contextual crop
- when `--full-page-primary` is used, those two point to the full-page versions instead

## Comment Style Templates

Use these as reusable defaults when the user asks for a "fixed template".

### 1) 高赞文艺风
Use when the post is inspirational, emotional, or human-interest:
- 真正的强大，不是……而是……
- 她用奔跑写下的，不只是……更是……
- 把磨难活成勋章，把奔跑写成答案，这就是……

Characteristics:
- slightly literary
- concise
- emotionally resonant
- not overly polished

### 2) 普通网友口语风
Use when the user wants something casual and natural:
- 这活动挺有意思，……
- 看着挺感动的，……
- 真的挺让人佩服的……

Characteristics:
- everyday language
- short sentences
- no official/newsroom tone

### 3) 温和克制风
Use when the user wants a balanced tone between literary and conversational:
- 以奔跑对抗命运，以坚持照亮前路……
- 把风雨走成坦途，把困境活成光芒……
- 一步一步，把命运跑赢……

Characteristics:
- polished but not grandiose
- suitable for high-quality comment sections

### Selection rule
- If the user says "高赞", prefer template 1.
- If the user says "口语", prefer template 2.
- If the user says "文艺一点但别太满", prefer template 3.
- If the user gives a reference sentence, mirror its rhythm and emotional intensity rather than copying its wording exactly.

### Rollback rule
If the first posted comment is off-topic, the page is a different post than expected, or the tone is wrong:
1. Inspect the current post text with `browser_console` before acting.
2. Delete the wrong comment if it was posted to the wrong target.
3. Re-navigate to the correct URL or reopen the login entry if the page state drifted.
4. Repost using the appropriate template.
5. Re-capture evidence.
