---
name: worktree-space
description: Create a Worktrunk-managed worktree and matching herdr space from an issue number plus title, or from a supplied worktree name.
---

# Worktree Space

Create one Worktrunk-managed Git worktree and one matching herdr space.

The script is the source of truth for repo detection, branch slugging, `wt new`,
checkout-path resolution, and herdr registration. The agent supplies only the
human name.

## Workflow

1. Resolve the name.
   - If the user gives an issue number, find the issue title from the cheapest reliable source: repo-local docs/manifests first, then the configured tracker.
   - If no title is available, ask one short question for the title.
   - Completion criterion: have either `<issue-number> <title>` or a plain worktree name.

2. Run the deterministic script.
   - From the current repo or worktree, run:

     ```bash
     "$HOME/.agents/skills/worktree-space/scripts/worktree-space.sh" <issue-number> "<title>"
     ```

   - For non-issue work:

     ```bash
     "$HOME/.agents/skills/worktree-space/scripts/worktree-space.sh" "<worktree name>"
     ```

   - Do not manually run `wt new`, `git worktree`, or `herdr worktree open` unless the script itself fails and the failure says what manual command to run.
   - Completion criterion: the script exits `0` and prints `branch`, `checkout_path`, `label`, and `already_open`.

3. Report the result.
   - Include the script's branch, checkout path, herdr label, and `already_open`.
   - Mention if herdr was skipped because `HERDR_ENV` was not set.
