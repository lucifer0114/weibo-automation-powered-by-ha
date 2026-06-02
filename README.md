# Automation powered by HA

Snapshot of the comment-evidence automation workflow, versioned through GitHub releases for traceable reliability iterations.

## Included
- Hermes skill bundle under `skill/`
- Skill references under `skill/references/`
- Primary Playwright automation script under `script/`
- Regression tests under `tests/`

## Purpose
- preserve a clean standalone repo for iterative hardening
- make each verified milestone easy to reference from GitHub Releases
- keep script, skill notes, and regression coverage aligned

## Current release
- Latest: [`v1.0.2`](https://github.com/lucifer0114/automation-powered-by-ha/releases/tag/v1.0.2)
- Previous baseline: [`v1.0.1`](https://github.com/lucifer0114/automation-powered-by-ha/releases/tag/v1.0.1)
- Original snapshot: [`V1.0.0`](https://github.com/lucifer0114/automation-powered-by-ha/releases/tag/V1.0.0)

## Version history

### `v1.0.2`
**Changed**
- updated the README to reflect the current release line and version progression
- further reduced public-facing wording exposure while keeping the repository purpose and release trail intact

**Added**
- `docs/plans/2026-06-02-v1.0.2-development-checklist.md` as a dedicated checklist for the next hardening cycle
- a clearer planning summary for the next milestone: shared finalization, machine-readable artifact output, stronger submission verification, and cleaner downstream artifact metadata

### `v1.0.1`
**Added**
- structured single-line evidence output via `EVIDENCE=<json>`
- final run summary output via `FINAL_SUMMARY=<json>`
- expanded regression coverage for evidence and reliability behavior

**Changed**
- stronger wait and submission-verification hardening in the automation flow

## Dependencies required to run `v1.0.2`
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
- A usable authenticated browser session is still needed for real comment/like actions

### Local runtime assumptions in this repo
- a persistent Playwright profile is expected
- a local screenshot output directory is expected
- the skill file still contains some environment-specific reference paths from the original Hermes workspace

## Notes
- This repository was exported from the local Hermes environment and then iterated independently
- Runtime-specific paths inside the skill/script are intentionally preserved as-is
- `v1.0.1` can be treated as a recoverable GitHub source backup, but not as a zero-setup portable executable bundle
