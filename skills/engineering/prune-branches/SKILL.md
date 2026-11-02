---
name: prune-branches
description: >-
  Prune merged PR branches, local and remote, with their worktrees. Use after a
  PR merges or when the user asks to clean up branches.
---

# Prune merged PR branches

A branch is **prunable** when a PR from it merged, with the branch's current
tip as its head, into a target that still exists on the remote; no open PR uses
it; and the PR passed policy (no bypass). Any target counts, so repositories
that merge into both `master` and `develop` need no `--base`; pass `--base` only
to narrow the plan. PR targets, `main`, `master`, `develop`, `release/*`, and
any `--protect <glob>` are never pruned. A local branch is also kept while its
worktree is dirty or **occupied** by a running process, since another agent
session may be working there, or while the main checkout has it checked out.
`scripts/prune_branches.py` owns these rules; it supports Azure DevOps (`az`)
and GitHub (`gh`) remotes and removes worktrees with `wt`.

1. Plan: `python3 -I <skill-dir>/scripts/prune_branches.py --repo <checkout>`.
   It fetches with prune and prints one `delete` or `keep` line per PR branch,
   then a `plan digest`. **Complete when** the plan and digest have printed.
2. Show the user the full `delete` list, with the `keep` lines and their
   reasons, and get approval of that exact list. **Complete when** the user
   approves the list.
3. Apply: rerun the same command with `--apply <digest>`. The script recomputes
   the plan and refuses when its digest differs (a PR merged or a branch moved
   since approval); then return to step 2 with the new plan. Remote deletes push
   with a SHA lease per branch; local deletes compare-and-delete on the planned
   SHA. A rejected lease or failed worktree removal prints a `failed` line and
   the rest of the plan still runs. **Complete when** the run exits 0, or on
   failure you report the `failed` lines and rerun the plan to show what is
   left.
4. Report what was deleted and each kept branch's reason. Occupied worktrees
   become prunable once their session ends.
