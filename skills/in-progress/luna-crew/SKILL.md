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

Settle architecture and open questions with the user first; those are yours.
Then cut the work into **lanes** and tasks.

A lane is one standing worker named for the workstream it owns, the way the
user thinks about it: `api`, `cli`, `web`, `importer`, `reviewer`. Use a short
lowercase name (`[a-z][a-z0-9-]*`) and never a task number or `worker-1`. Its
pane is labelled `<lane> · <focus>`, so the user can see who does what. Keep a
worker for at most three briefs. Before the fourth brief, or sooner when the
next task is outside its context, close its pane and start a fresh worker with
the same lane name. Propose the lanes to the user along with the plan.

Then cut each lane's work into tasks. Each task is one of **scout**,
**implement**, or **fix**, has disjoint file ownership from every task running
alongside it (or its own worktree via `/worktree-space`), and has a completion
criterion the worker can check without you.

Completion criterion: `PLAN.md` lists every task with its owned paths and its
criterion, and the decisions the user made are recorded.

## 2. Brief and launch

Write each `BRIEF.md` with these sections, briefly:

- **Contract**: `Follow $HOME/.agents/skills/luna-crew/WORKER.md.`
- **Goal**: what is to be produced, and why.
- **Decisions**: the architecture already chosen. The worker builds on these
  and does not revisit them.
- **Scope**: owned paths; paths it may read but not change.
- **Done when**: the checkable criterion and the verification commands to run.

Start and brief workers with the script:

```sh
luna.sh start <lane> "<focus>" [--from <pane>] [--direction right|down]
luna.sh brief <lane> .scratch/luna/<task>/BRIEF.md
```

`<focus>` is a few words on what the lane is doing now (`tengella cli`,
`route seam`). When the lane's focus changes, or an idle worker moves to
another lane, relabel it before briefing:

```sh
luna.sh rename <lane> <new-lane> "<focus>"
```

`start` prints `<lane> <pane> ready`. Exit code `3` with `blocked-startup`
means Codex is asking to trust the folder. Answer
`herdr agent send-keys <lane> enter` only for a repository the user asked you
to work in, then brief.

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

Review the diff against the brief's decisions and scope: `git diff --stat`,
then the files where the design risk is. Trust the handback's verification
evidence. Run a check yourself only for the final gate before a commit, or
when the evidence is missing or contradicts the diff.

Then pick one:

- **Accept**: commit using the handback's proposed message, adjusted as
  needed. You own commits; workers stage only.
- **Fix**: put corrections or new directions in a new `BRIEF.md` of kind
  `fix`, then brief the worker. Keep steering in briefs; answer a `blocked`
  worker inline in its thread.
- **Escalate**: an open question in the handback that is an architecture or
  product decision goes to the user.

For a bug hunt, make one task whose Done-when is the failing command going
**red → green**. Point its worker to the `diagnosing-bugs` skill.

Update `PLAN.md`. Completion criterion: every task in `PLAN.md` is accepted,
or escalated with the user's answer recorded.

## Context budget

Use one orchestrator session per workstream, started in the repository or
worktree and resumed from `.scratch/luna/PLAN.md`. Compact at every PLAN
milestone and whenever context passes about 300k tokens. Claude Code's
auto-compaction at 30% is a backstop. Close a finished worker with
`herdr pane close <pane>` when it will not get follow-up work.
