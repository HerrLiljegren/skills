---
name: luna-crew
description: Orchestrate Luna 6 workers (Codex gpt-6-luna) in Herdr panes. The orchestrator keeps architecture, decisions, discussion, and final review; Luna scouts, implements, and verifies. Use when the user asks for Luna, Luna 6 agents, or Luna workers.
---

# Luna crew

You are the **orchestrator** (Claude, or Codex on `gpt-6-astra`). Luna 6
**workers** are Codex `gpt-6-luna` agents in sibling Herdr panes. The split
exists for weekly limits: an orchestrator turn re-reads a large context, while
Luna quota is cheap. Spend orchestrator turns on judgement; send every
bounded, checkable task to a worker.

| Orchestrator owns | Luna owns |
|---|---|
| architecture and design decisions | **scouting**: reading code, docs, logs; writing findings |
| discussion and questions with the user | **implementation** within a brief |
| the plan and the briefs | **verification**: builds, tests, formatters, with log paths |
| final review and commits | fixups from review notes |

Your own code reading is limited to what a decision or a review needs. When
you need to understand an area, write a scout brief.

Requires `HERDR_ENV=1`. `scripts/luna.sh` (beside this file) owns all Herdr
plumbing; the `/herdr` skill is for anything the script does not cover.

## Workspace

All coordination lives in `.scratch/luna/` at the repository root. Make sure
`git check-ignore -q .scratch/` succeeds; otherwise add `.scratch/` to
`.git/info/exclude`.

- `.scratch/luna/PLAN.md`: the **ledger**: goal, decisions taken, and one row
  per worker task (lane, brief, status, outcome). Update it after every step
  that changes state. It is how a fresh or compacted session resumes.
- `.scratch/luna/<task>/BRIEF.md`: written by you.
- `.scratch/luna/<task>/HANDBACK.md`: written by the worker.

## 1. Plan

Before implementation, settle meaning, shape, and verification:

- **Meaning**: read the applicable glossary and ADRs. Use the domain-modeling
  skill when terms or relationships are new, ambiguous, or changing; resolve
  them with concrete scenarios and code evidence. Capture resolved domain
  terms in the glossary and offer ADRs only under that skill's criteria.
- **Shape**: use the codebase-design skill when an interface, responsibility,
  repeated pattern, or test seam needs a decision. Reuse settled designs;
  record the chosen structure and its rationale in the brief.
- **Verification**: design the test scenarios and public seams yourself;
  workers write and execute the tests. Reuse existing coverage where
  sufficient. Resolve required seam approval with the user before dispatch,
  carrying forward approval already given. Record the
  affected checks and repository-required gates.

Unresolved product or architecture decisions stay with you and the user;
a scout may gather the facts, but implementation starts only after its
decisions are settled.
Then cut the work into **lanes** and tasks.

A lane is one standing worker named for the workstream it owns, the way the
user thinks about it: `api`, `cli`, `web`, `importer`, `reviewer`. Use a short
lowercase name (`[a-z][a-z0-9-]*`) and never a task number or `worker-1`. Its
pane is labelled `<lane> · <focus>`, so the user can see who does what. Keep a
worker for at most three briefs. Before the fourth brief, or sooner when the
next task is outside its context, close its pane and start a fresh worker with
the same lane name. Propose the lanes to the user along with the plan.

Then cut each lane's work into tasks. Each task is one of **scout**,
**implement**, **fix**, or read-only **review**, has disjoint file ownership
from every task running alongside it (or its own worktree via
`/worktree-space`), and has a completion criterion the worker can check
without you.

Completion criterion: `PLAN.md` lists every task with its owned paths and its
criterion, and the domain contract, design decisions, and authorized test
seams needed by each implementation task are recorded.

## 2. Brief and launch

Write each `BRIEF.md` with these sections, briefly:

- **Contract**: `Follow $HOME/.agents/skills/luna-crew/WORKER.md.`
- **Workflow**: for implement/fix tasks, explicitly request the implement
  skill with the crew adaptations in `WORKER.md`: worker TDD and affected
  checks; orchestrator-owned independent review and commits. This carries
  the user's authorized crew workflow into the worker request.
- **Goal**: what is to be produced, and why.
- **Decisions**: the architecture already chosen. The worker builds on these
  and does not revisit them.
- **Shape**: the structure settled in step 1, including the interface and
  test seams. Reference existing designs where sufficient; omit for tasks
  that require no design decision.
- **Test scenarios**: for implement/fix tasks, specify each behavior and
  public seam, concrete inputs, expected results with an independent source
  (spec, domain decision, or worked example), the defect it must catch and
  why it should go red, and relevant constraints such as tenancy,
  authorization, or ordering. Reference existing tests where sufficient;
  state why no new test is needed when applicable. You own test intent;
  the worker owns fixture mechanics, assertions, and execution.
- **Scope**: owned paths; paths it may read but not change.
- **Done when**: the checkable criterion and the verification commands to run.

Before launch, verify every referenced existing file in the target worktree
at its starting commit. Mark paths to be created as new; correct stale paths
before briefing. Record the starting SHA and pre-existing changes in owned
paths in `PLAN.md`, so the later review can isolate this task. Verify
external skill paths against their installed locations.

Start and brief workers with the script:

```sh
luna.sh start <lane> "<focus>" [--from <pane>] [--direction right|down]
luna.sh brief <lane> .scratch/luna/<task>/BRIEF.md
```

| Lane | Model and effort |
|---|---|
| scout, implement, fix | default: `gpt-6-luna`, medium; `--effort high` for a hard lane |
| review | `--model gpt-6.1-sol --effort high` |

`<focus>` is a few words on what the lane is doing now (`tengella cli`,
`route seam`). When the lane's focus changes, or an idle worker moves to
another lane, relabel it before briefing:

```sh
luna.sh rename <lane> <new-lane> "<focus>"
```

`start` prints `<lane> <pane> ready`. Exit code `3` with `blocked-startup`
prints the worker's screen. Answer a folder-trust prompt with
`herdr agent send-keys <lane> enter` only for a repository the user asked you
to work in; send any other prompt to the user.

Completion criterion: every launched worker is reported `working` by `brief`.

## 3. Wait

Make one blocking call per round:

```sh
luna.sh wait <lane> [<lane>...]
```

It returns `<lane> <status>` as soon as any worker stops working. Claude Code:
run it in the background and end your turn; the harness re-invokes you when
it exits. Codex: call the wait with `yield_time_ms: 30000` (the Codex 0.160
maximum) and a small `max_output_tokens`. On each yield, re-enter the wait in
the same session with `yield_time_ms: 30000` until it exits. The script does
the polling; your turns go to handbacks.

## 4. Review the handback

For the returned lane:

- `blocked`: run `herdr agent read <lane> --source recent --lines 40` once,
  answer the approval or question within the brief's scope, return to step 3.
- `done` or `idle`: read `HANDBACK.md`. A worker that stopped without a
  handback gets one prompt to write it.

Review the task diff against the brief's decisions and scope, including
committed, staged, unstaged, and new files since its recorded baseline.
Read the handbacks and diff stat, then open only files named by review
findings; account for pre-existing edits separately. Trust the handback's
verification evidence.
Run a check yourself only when required evidence is missing, contradicts the
diff, or has become stale after relevant changes.

For **implement** and **fix** handbacks, obtain independent Standards and
Spec reviews before acceptance. Use separate fresh `reviewer-standards` and
`reviewer-spec` workers that did not implement the change, started with the
review model from the table. Each read-only brief names the exact task diff and
baseline, the implementation brief, and
applicable standards files (including nested
`CODING_STANDARDS.md` files). Use the code-review skill's axis-specific
prompts and smell baseline as their source of truth. Standards checks
maintainability and the brief's Shape, separating violations from judgement
calls. Spec checks the originating requirements, settled domain contract, and
whether tests establish the brief's scenarios.
The brief complements the spec rather than replacing it. Identify the spec
before dispatch; if unavailable, record the missing evidence and resolve the
review scope with the user. Keep the axes separate in the handbacks and
ledger. Reuse verification evidence.

Read both reviewers' handbacks and resolve every finding: fix, explain a
dismissal, or escalate a decision. Review the resulting fix diff before
acceptance. Record the reviewed revision and dispositions in `PLAN.md`;
changes after that revision require review of the changed portion. Scout and
review handbacks need no further reviewer.

Then pick one:

- **Accept**: stage exactly the brief's owned paths with
  `git add -- <owned paths>`, check `git diff --cached --stat` against the
  handback, then commit using the handback's proposed message, adjusted as
  needed. You own staging and commits.
- **Fix**: put corrections or new directions in a new `BRIEF.md` of kind
  `fix`, then brief the worker. Keep steering in briefs; answer a `blocked`
  worker inline in its thread.
- **Escalate**: an open question in the handback that is an architecture or
  product decision goes to the user.

For a bug hunt, make one task whose Done-when is the failing command going
**red → green**. Point its worker to the `diagnosing-bugs` skill.

Update `PLAN.md`. Completion criterion: every task in `PLAN.md` is accepted,
or escalated with the user's answer recorded; accepted code changes have an
independent review with every finding resolved for the accepted revision.

Before reporting completion, close finished worker and reviewer panes with
`herdr pane close <pane>` after their handbacks are saved and findings are
resolved. Retain a pane only for planned follow-up work, recording why in
`PLAN.md`. Close only crew panes created for the task or explicitly
authorized for cleanup; preserve the orchestrator and unrelated panes.
Verify the remaining panes and record cleanup in `PLAN.md`.

## Context budget

Use one orchestrator session per issue, started in the repository or
worktree and resumed from `.scratch/luna/PLAN.md`. When an issue's tasks are
accepted, start a fresh session from `PLAN.md` rather than continuing to
compact. Compact at every PLAN milestone and whenever context passes about
300k tokens. Claude Code's auto-compaction at 30% is a backstop.
