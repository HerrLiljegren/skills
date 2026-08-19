---
name: worktree-closeout
description: Deliver and close one approved issue worktree without a pull request.
disable-model-invocation: true
---

# Worktree Closeout

Close one completed issue through the repository's direct-commit workflow. Run
this skill from a root orchestrator that will survive removal of the target
worktree and Herdr workspace.

Examples:

```text
/worktree-closeout 5378
/worktree-closeout issue/5378-migrate-the-six-ops-batch-scripts-to-v3 develop
```

## 1. Resolve one closeout target

Read the applicable host and repository instructions before inspection.
Resolve the repository from the current checkout, then resolve the first
argument as follows:

- A numeric issue selects the worktree whose checked-out branch matches
  `issue/<number>-*`.
- A branch selects its exact checked-out worktree.
- A path selects that exact worktree after canonicalization.

Use Git's worktree metadata as the source of truth. A numeric issue does not
reconstruct the slug from the current tracker title. Continue only when the
selector matches exactly one linked worktree.

Resolve the target branch from the optional second argument or Worktrunk's
reported repository default. Record the parent repository, source branch,
canonical worktree path, target branch, issue number, and current source HEAD.

When running inside Herdr, resolve the workspace by exact checkout path and
repository root. Record its explicit workspace ID and verify it differs from
the root orchestrator's workspace. If the orchestrator is inside the workspace
being closed, stop with a handoff for a surviving orchestrator.

Completion criterion: every local and Herdr identity is exact and unique, and
the orchestrator will survive target removal.

## 2. Establish closeout evidence

Read the complete work item, comments, relations, acceptance criteria, and
verification notes through the repository's configured tracker workflow.
Confirm the item belongs to this repository, is assigned correctly, and is in
a state that permits delivery.

Read the live work-item type metadata and its transitions. Resolve the exact
terminal state available from the item's current state; repository prose is
guidance, not a substitute for the tracker schema. Stop if the tracker cannot
prove one exact transition.

Inspect the complete source-branch status and diff, including staged,
unstaged, and untracked files. Account for every change because standard
`wt merge` stages all changes by default. Confirm required reviews and
verification are complete, acceptance criteria are satisfied, no secret or
credential material is present, and any remaining follow-up is linked or
recorded according to repository policy.

Fetch the target remote. Confirm the local and remote target are compatible
with a direct push and that the source can enter the standard Worktrunk merge
flow. Treat Worktrunk and installed command help as the source of truth for
current command behavior.

Completion criterion: every change and acceptance criterion is accounted for,
verification evidence is named, the intended remote target is current and
pushable, and the exact tracker transition is proven.

## 3. Obtain the delivery gate

Present one compact gate containing:

- issue ID, title, current state, proposed terminal state, and assignee
- source branch, worktree path, and Herdr workspace ID
- target branch and remote
- files and commits included by the squash
- verification performed and still outstanding
- tracker changes and follow-ups
- the exact effects: commit/squash, merge, push, issue closeout, worktree and
  branch removal, and Herdr workspace closure

Continue only after the user explicitly approves that resolved gate. A general
request to inspect, review, or prepare closeout is not approval to deliver.

Completion criterion: the user has approved the exact issue, changes, target,
remote delivery, tracker mutation, and cleanup effects.

## 4. Deliver and close the issue

From the surviving orchestrator, run standard `wt merge` against the resolved
worktree and explicit target branch:

```bash
wt -C "$worktree_path" merge "$target_branch" --yes --format json
```

Preserve repository commit conventions and issue-reference requirements. Stop
on any conflict or failed hook and report the retained recovery state.

After a successful merge:

1. Resolve the final target-branch commit.
2. Push the target branch to the approved remote.
3. Fetch the remote target and prove it contains that exact commit.
4. Link the final target commit to the issue.
5. Post concise closeout evidence covering target containment, verification,
   acceptance criteria, and residual risk.
6. Move only the delivered issue to the exact terminal state approved in the
   gate. Parent and related work items require their own explicit authority.

If remote delivery or tracker closeout fails, stop and report the exact partial
state. The issue remains open until remote containment and required evidence
are proven. A rejected tracker value requires a new gate before attempting a
different state.

Completion criterion: the exact final commit is on the approved remote target,
linked to the issue, and the issue is closed with complete evidence.

## 5. Retire the local workspace

Verify Worktrunk removed the source worktree and branch. When cleanup is still
finishing in the background, wait boundedly and re-check rather than guessing.

If a Herdr workspace was recorded, re-read it by explicit ID, verify it still
identifies the resolved checkout, then close that workspace. Never select a
workspace from focus or a partial label.

Report the issue URL and state, final target commit, verification evidence,
removed branch and worktree, and closed Herdr workspace ID from the surviving
orchestrator.

Completion criterion: delivery and tracker evidence remain reachable, the
source branch and worktree are gone, the exact Herdr workspace is closed, and
the orchestrator has reported the final state.
