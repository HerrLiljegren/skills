---
name: afk
description: Trigger this is the user says 'full send'.
---

# AFK

Implement one issue produced by `/triage` until:

- CI passes on the PR.
- Every acceptance criterion has evidence in the PR body: a test, a command and its output, or a
  screenshot.
- An independent review found nothing left to fix (step 4).

## 1. Read the issue

Read the issue, its decisions and its reproduction. If something needed to proceed is missing or
contradicts the code, ask through the harness's question tool (Claude Code: `AskUserQuestion`;
Codex: its user-input tool) so it raises a notification, then wait. Ask rather than guess.

## 2. Prepare each repository

For each repository, in the issue's landing order, work on a fresh branch in its own worktree off
the current default branch.

## 3. Implement in landing order

For a defect, first turn the reproduction into a failing test.

Producer first: implement, test, and run it (through Aspire where the repo has an AppHost) to show
the new behaviour working. Then the consumer, built and tested against the running producer, not a
mock of what it should do.

## 4. Review

Hand the diff and the issue to a fresh reviewer (a subagent or new session with no implementation
context). It checks the diff against the acceptance criteria and the repo's standards. Fix what it
finds and review again until it finds nothing.

## 5. Open the PRs

One PR per repository, each linking the issue and, for multi-repo work, its sibling PR. In the PR
body include the acceptance-criteria evidence and a **risk call**: whether this change would be safe
to merge without human review, and why. Merging stays manual for now; the risk calls are the record
for deciding later whether low-risk work can skip review.

Done when every PR is green. Move the issue to In Review and report the PR links. Merging is the
human's; `/close` follows the merge.
