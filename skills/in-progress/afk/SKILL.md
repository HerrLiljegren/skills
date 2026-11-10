---
name: afk
description:
  Implement one /triage issue to verified PRs waiting for human review. Use when the user says "full
  send" or invokes /afk with an issue.
---

# AFK

Implement one issue produced by `/triage` until every repository it names has a PR waiting for human
review, with:

- Evidence in the PR body for every acceptance criterion: a test, a command and its output, or a
  screenshot.
- A **PASS** verdict from an agent that did not write the code (step 4).
- CI finished and passing, so the human never reviews a PR with failing checks (step 6).

## 1. Read the issue

Read the issue, its decisions and its reproduction. When a fact is missing, find it out: read the
code or run the system. Ask only for a decision that the issue, the code and the running system
cannot settle, or one that is hard to undo. The issue's **Authorizations** are already granted; do
not ask for them again. Ask through the harness's question tool (Claude Code: `AskUserQuestion`;
Codex: its user-input tool) so it raises a notification, then wait.

## 2. Prepare each repository

For each repository, in the issue's landing order, work on a fresh branch in its own worktree off
the current default branch.

## 3. Implement in landing order

For a defect, first turn the reproduction into a failing test.

Producer first: implement, test, and run it to show the new behaviour working. Then the consumer,
built and tested against the running producer, not a mock of what it should do. Run the system the
way the repo provides: its verification skill if it has one, otherwise its Aspire AppHost.

## 4. Verify

Hand the issue and the branches to a fresh agent with no implementation context. It runs each
acceptance criterion the way a user would, on the base branch and on the head, and returns **PASS**,
**PASS+NOTES** or **FAIL** with the evidence for each criterion.

It reports a defect only with proof it ran: a failing test, a script, or command output. Style,
naming, structure and risks that need a future change to matter are not findings.

On FAIL, fix and verify again with a new agent. If the harness cannot start one, do not verify your
own work: record "verdict missing" in the PR and the risk call, and carry on.

## 5. Open the PRs

One PR per repository, each linking the issue and, for multi-repo work, its sibling PR. Write the
body with the `pr` skill: it carries the evidence, the verdict, the checks left to the human and the
**risk call** (whether this change would be safe to merge without human review, and why). Merging
stays manual for now; the risk calls are the record for deciding later whether low-risk work can
skip review.

## 6. Hand back

Wait for CI on every PR before handing back. Stay in the run while it runs: poll its status with the
repo's CLI rather than ending the turn and counting on being woken later. If a check fails, fix,
push, and wait again. If CI has not finished after an hour, hand back and say which checks are still
running.

When the verdict is PASS or PASS+NOTES, tick each acceptance criterion in the issue that the
verifier proved: edit its `- [ ]` to `- [x]` in place, without rewriting the rest of the
description. Tick only on the verifier's evidence, never on the implementer's word. A criterion
stays unticked when it failed, was not run, or is a human gate. List the unticked criteria in the
hand-back.

Write the hand-back, and any blocker or question on the way, so it reads in ten seconds. Put what
the human must do first; leave out SHAs, revisions and ownership notes; link the details instead of
pasting them:

```text
DEV-42 · Ignite cache misses → Redis      PR #5758 · CI ✅ · PASS
Solves: each of 7 instances reloaded the tenant partition; now one load is shared.

You need to:
- [ ] Manual check after release: Seq shows at most one load per tenant
      Not automated: needs production traffic
      Could automate: verify-webgui journey "edit card twice"

Details: artifacts/dev42/evidence.md
```

A blocker says in one line what is blocked, then the decision needed, with options and a
recommendation. Every manual check says why it is not automated and whether a verification journey
could cover it.

Done when every PR is open with its checks passed, the issue is In Review with its ticked criteria
matching the verdict, and the hand-back gives the PR links, the verdict and the unticked criteria.
Merging is the human's; `/close` follows the merge.
