# weibo-comment-evidence-snapshot

Snapshot of the Weibo comment evidence workflow, now versioned through GitHub releases for traceable reliability iterations.

## Included
- Hermes skill: `skill/SKILL.md`
- Skill references: `skill/references/*.md`
- Playwright script: `script/weibo_manual_comment_flow.py`
- Regression tests: `tests/*.py`

## Purpose
- preserve a clean standalone repo for iterative hardening
- make each verified milestone easy to reference from GitHub Releases
- keep script, skill notes, and regression coverage aligned

## Current release
- Latest: [`v1.0.1`](https://github.com/lucifer0114/weibo-automation-powered-by-ha/releases/tag/v1.0.1)
- Previous baseline: [`V1.0.0`](https://github.com/lucifer0114/weibo-automation-powered-by-ha/releases/tag/V1.0.0)

## What `v1.0.1` adds
- structured single-line evidence output via `EVIDENCE=<json>`
- final run summary output via `FINAL_SUMMARY=<json>`
- stronger wait / submit verification hardening in the comment workflow
- expanded regression coverage for evidence and reliability behavior

## Dependencies required to run `v1.0.1`
This release is a **source snapshot**, so a new machine still needs the runtime dependencies below.

### Python packages
- Python `3.10+` recommended
- `playwright`
- `Pillow`
- `pytest` (recommended for verification, not strictly required for runtime)

Example install flow:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install playwright pillow pytest
python -m playwright install chromium
```

### Browser/runtime requirements
- Chromium browser installed through `playwright install chromium`
- On Linux, Playwright system libraries may also be required
- A usable Weibo login session is still needed for real comment/like actions

### Local runtime assumptions in this repo
- default Playwright profile dir: `~/.playwright-weibo-profile`
- default screenshot output dir: `~/outputs/weibo-comment-shots`
- the skill file still contains some environment-specific reference paths from the original Hermes workspace

## Notes
- This repository was exported from the local Hermes environment and then iterated independently
- Runtime-specific paths inside the skill/script are intentionally preserved as-is
- `v1.0.1` can be treated as a recoverable GitHub source backup, but not as a zero-setup portable executable bundle
