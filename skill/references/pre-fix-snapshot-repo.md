# Pre-fix snapshot repo pattern for Weibo automation

Use this pattern when the user wants a clean backup of the current Weibo automation state *before* reliability fixes.

## When this applies
- The working `hermes-agent` repository has unrelated local changes.
- The user wants a repair baseline or archival copy.
- The goal is to preserve only the Weibo automation assets, not the whole monorepo/worktree.

## Preferred approach
1. Create a new standalone snapshot repository outside the main `hermes-agent` worktree.
2. Copy only the relevant assets:
   - `SKILL.md`
   - `references/`
   - the automation script (for this environment: `weibo_manual_comment_flow.py`)
   - a short `README.md`
   - a small `.gitignore` for caches / outputs
3. Commit that snapshot as the pre-fix baseline.
4. Push it to a dedicated GitHub repository.
5. After pushing, reset the local remote URL to a plain non-token HTTPS URL and verify the local repo is not left pointing at a credential-bearing remote.

## Why
- Avoids polluting the snapshot with unrelated edits from `hermes-agent`.
- Preserves a clean rollback point before touching fragile selectors / login / evidence logic.
- Makes later diff review much easier because only the Weibo automation files are present.

## Scope rule
Prefer a focused archive over "just push the current repo". For this workflow, the snapshot should contain only the Weibo skill/script bundle unless the user explicitly asks for a wider backup.

## Backend decision rule
Do not treat Browserbase / Browse.sh migration as the default next step after archiving. The dominant risks in this workflow are usually login state, verification, selector scope, and screenshot attribution, which remain local-skill concerns even if the browser backend changes.
