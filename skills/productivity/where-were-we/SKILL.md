---
name: where-were-we
description: Reconstruct current work context and produce a concise "Where were we, where are we, where are we going" brief. Use when the user asks to catch up, resume, reorient, remember the current state, summarize active work, inspect what happened in a branch, check touched issues, review pane history, or asks "where were we?".
---

# Where Were We

Produce an evidence-backed catch-up brief before doing more work.

## Workflow

1. Identify the workspace.
   - Run `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, and `git status --short --branch` when inside a Git repo.
   - If inside a linked worktree, resolve the parent repo with `git rev-parse --git-common-dir`.
   - If inside herdr (`HERDR_ENV=1`), run `herdr workspace list` and `herdr pane list`; identify the focused pane and sibling panes in the same workspace.
   - Completion criterion: know the cwd, repo root, branch, worktree/parent relationship, focused herdr workspace, and whether the tree is dirty.

2. Read recent pane history.
   - If in herdr, read the focused pane recent history with `herdr pane read <pane> --source recent --lines 120`.
   - Read sibling panes in the same workspace when they look relevant: agents, running servers, tests, logs, or shells in the same repo/worktree.
   - If not in herdr, inspect tmux only when available and relevant: `tmux list-sessions`, then panes/windows whose session path matches the repo.
   - Completion criterion: have the last visible user intent, agent actions, running commands, and any blocked/done agent states relevant to this workspace.

3. Recover Git story.
   - Run `git status --short`, `git diff --stat`, `git diff --name-status`, and `git log --oneline --decorate --max-count=12`.
   - If the branch tracks an upstream, compare with upstream: `git status --short --branch`, `git log --oneline --left-right --cherry-pick @{upstream}...HEAD`, and `git diff --stat @{upstream}...HEAD`.
   - If no upstream exists, compare against the likely base branch only after discovering it from repo conventions, recent branches, or Worktrunk metadata; avoid guessing silently.
   - Completion criterion: know uncommitted changes, recent commits, ahead/behind state when available, and the likely base or explicitly say it is unknown.

4. Find issue/work-item context.
   - Extract issue numbers from branch name, herdr label, pane history, recent commits, changed docs, and filenames.
   - Check repo-local issue sources first: `docs/issues/manifest.json`, `docs/issues/*`, `docs/agents/*`, `.agents/*`, PRD/prompt files, and issue comments/handoff files mentioned in recent history.
   - If Azure DevOps, GitHub, or another tracker tool is configured and needed, inspect the referenced issues read-only.
   - Completion criterion: list every plausible touched issue with title/status when available, or state that no issue source was found.

5. Inspect project signals.
   - Check changed tests, failed logs, TODO/handoff notes, and recent verification commands from pane history.
   - If a package/app has obvious verification commands, report them as candidate next checks; do not run expensive tests unless the user asked to validate.
   - Completion criterion: know what has been verified, what is unverified, and what command would most directly reduce uncertainty.

6. Write the brief.
   - Keep it compact and operational.
   - Separate facts from inference.
   - Do not hide uncertainty; name missing evidence and the cheapest way to resolve it.

## Output Shape

Use this shape unless the user requests a different format:

```md
**Where We Were**
- Last intent:
- Recent actions:
- Relevant issue/work item:

**Where We Are**
- Repo/branch:
- Worktree/herdr:
- Git state:
- Verification:
- Open risks:

**Where We Are Going**
- Next best step:
- Then:
- Stop/ask point:
```

## Guardrails

- Stay read-only unless the user explicitly asks to continue implementation.
- Do not summarize from memory alone when local evidence is cheap to inspect.
- Prefer exact file paths, branch names, issue IDs, commit SHAs, and command outputs over vague recap.
- If the workspace is not a Git repo and no herdr/tmux context is available, say so and ask what context to anchor on.
