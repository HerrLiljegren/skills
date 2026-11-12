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
- A **PASS** verdict from an agent that did not write the code (step 6).
- CI finished and passing, so the human never reviews a PR with failing checks (step 8).

Two rules for the whole run, so the human always hears back:

- Never end a turn on a question or a choice written as text: it raises no notification and the
  thread looks finished. Ask through the question tool, or hand back.
- Do not babysit work that runs for more than about an hour (a long query, a slow pipeline) with
  background monitors. Hand back with what is in hand and what is still running.

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

Pass the repository's own checks before anything else: build, analyzers, formatting and any
complexity or architecture rule. A check that runs is cheaper than a reviewer and never loops.

## 4. Review the design

Start the `reviewer` agent once, with the issue and the diff. Where the harness cannot start it by
name, start a fresh agent on the **reviewer** role's model from host-local agent guidance. It sorts
its findings into **blocking** and **notes**.

Fix the blocking findings. Notes go to the PR body for the human; they never start a fix. There is
no second design review: the verifier checks the fixed version in step 6. When a blocking finding is
something an analyzer, test or architecture rule could catch, say so in the hand-back; it belongs in
a check, not in another review.

## 5. Draft the PR bodies

One PR body per repository, written with the `pr` skill before verification so the verifier can
check its claims. It carries the evidence, the design notes, the checks left to the human and the
**risk call** (whether this change would be safe to merge without human review, and why). Leave the
verdict section empty, and check it with the `pr` skill's check in `--draft` mode. Merging stays
manual for now; the risk calls are the record for deciding later whether low-risk work can skip
review.

## 6. Verify

Start the `verifier` agent with the issue, the branches and the PR body drafts. Where the harness
cannot start it by name (for example a delegation to another provider), start a fresh agent with no
implementation context on the **verifier** role's model from host-local agent guidance. It runs each
acceptance criterion the way a user would, on the base branch and on the head, checks every claim in
the PR bodies against its own runs, and returns **PASS**, **PASS+NOTES** or **FAIL** with the
evidence for each criterion. Paste its verdict and evidence into the PR body's verdict section as it
wrote them.

It fails only on an acceptance criterion or a false claim in a PR body. Anything else is a note for
the human, never a reason for another round.

On FAIL, fix and start a new verifier with the earlier findings and what you did about each. It
re-runs the failed criteria and claims, and quickly re-runs the ones that passed. After a second
FAIL on the same criterion or claim, stop and hand back with what failed and why: a rerun on higher
effort is the human's call. If the harness cannot start a verifier, do not verify your own work:
record "verdict missing" in the PR and the risk call, and carry on.

## 7. Open the PRs

Run the `pr` skill's check on each final body, without `--draft`, and fix every error. Open one PR
per repository with its body, each linking the issue and, for multi-repo work, its sibling PR.

## 8. Hand back

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
DEV-42 · Ignite cache misses → Redis      PR #5758 · CI ✅ · PASS · Guide ✅
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
