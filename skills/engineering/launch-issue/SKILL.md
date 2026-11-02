---
name: launch-issue
description: Launch selected Tengella Issues or Bugs into Herdr workers.
argument-hint: "issue [issue ...] [direction]"
disable-model-invocation: true
---

# Launch Issue

Launch the explicitly selected issues. Claude uses `/launch-issue`; Codex uses
`$launch-issue`. Read IDs and optional direction from the invocation text:

```text
/launch-issue 5421
$launch-issue 5421 5422 use medium reasoning, base both on latest master
/launch-issue 5421 focus on the Linux report-rendering seam
```

Accept positive issue IDs at the start, deduplicate them in order, and treat
remaining text as direction. Natural-language requests naming the selected IDs
are also valid. Resolve ambiguous IDs or conflicting options before mutation.
A bare invocation needs issue IDs. Quoted direction remains task data, never
shell code. These are agent inputs, not shell flags or harness substitutions.

The orchestrator owns preflight, claims and immutable handoffs. The companion
owns local worktrees, workspaces, workers and prompt submission. Each issue has
one worker and receipt. Invocation authorizes these steps; reuse that authority.
Launch ends at prompt acceptance. Delivery and later closeout remain separate.

## 1. Preflight the selection

Run `/tengella-workflow` for Azure DevOps interfaces, target routing and lifecycle
gates. Inspect the installed CLI's help for required operations. Read applicable
repository guidance once. Resolve organization, project, repository and Area Path
from that guidance; require organization `tengella`. Read the exact `origin`
from Git and verify its organization/project/repository against the route.
Git owns the remote URL; repository Markdown need not duplicate it. Verify live
repository identity through the workflow's supported interface before claiming.

Find existing launch receipts under `/tmp` by issue and repository identity
before deriving paths from today's title. Reuse exactly one matching receipt
and its immutable handoff; ambiguity blocks that item. An accepted launch is
an existing delivery: skip new-launch tracker/base/profile preparation and
validate it through the companion without reclaiming,
changing scope or sending another prompt. Report conflicting requested base,
profile or direction explicitly instead of applying them to the running worker.

For new launches and incomplete setup, pass the resolved project wherever the
command supports project selection.
For ID-based reads, require the returned `System.TeamProject` to match before
using the item. Fetch each complete context once and retain its fields, revision,
relations, comments and URL. Confirm Issue/Bug type, single-repository scope,
explicit AFK/HITL/Human mode and no conflicting owner or terminal state.

Check current-user evidence before assigning anyone. For an existing assignee,
use an exact project-scoped query for this ID and `AssignedTo = @Me`. Assignment
of an unassigned item requires canonical authenticated-user identity. Discover
actual CLI capabilities: repository lookup, current identity, and any transition
metadata required by the target adapter must be available. Internal APIs are
not CLI commands. Report missing capabilities together before tracker mutation;
the shared workflow owns interface selection.

Resolve the worker profile and base once for the selection unless the user gives
per-issue choices. Defaults: Codex, `gpt-6.1-sol`, `medium`, current branch/HEAD.
Pi requires an explicit provider/model and reasoning. For another base, resolve
a full commit SHA. For latest remote, use `git ls-remote` against the verified
origin and require one matching ref and that commit locally. Keep the invoking
checkout unchanged. Handoff details are in [handoff and receipt](references/handoff.md).

Run the read-only local preflight from the skill directory:

```sh
scripts/preflight.sh "<root>" "<organization>" "<project>" "<repository>" "<worker>"
```

It checks tools, Herdr caller context and repository resolution; it does not
establish tracker readiness or resolve an alternative launch base. If sandbox
access is denied, use the harness's narrowly scoped escalation for the same
check. A denied approval remains a blocker. Collect independent gaps in one
report rather than asking separately about each already-authorized step.

Evaluate the shared Ready gate and current dependencies for each new launch.
Distinguish agent-owned checks before Review, human acceptance at the Review
handoff, and unresolved decisions before implementation. AFK requires a reachable
Review stopping point. Reconcile contradictory criteria before claiming.

**Complete when** every selected item is classified as eligible, already launched
or blocked, with verified route/base/profile and explicit gaps. Shared failures
block the selection; item-specific failures leave independent eligible items
available. Report a compact preflight summary; no additional confirmation is
needed when scope and authority are already settled.

## 2. Claim and launch each eligible issue

Process independent eligible items in the requested order, completing this step
for one item before claiming the next. A batch is not an all-or-nothing tracker
transaction. Dependencies requiring another delivery to land remain unclaimed.

1. Re-read immediately before a claim. Compare scope and gate-relevant fields
   with the retained snapshot. If they changed, reassess before mutation; never
   combine stale requirements with a fresh claim. Verify the target implementation
   state using the repo adapter and live metadata required by the shared gate.
2. When state and current-user assignment already match, write nothing.
   Otherwise update only the differing fields with `--expected-revision`.
   Use the operation's verified readback; inspect exit-4 effects before any
   retry. A rejection or conflicting owner stops this item without rollback.
3. Build the immutable handoff from the verified snapshot and post-claim state,
   assignee and revision. Follow [handoff and receipt](references/handoff.md).
4. Invoke the companion once from the verified repository root:

   ```sh
   <skill-directory>/scripts/launch-worktree.sh /tmp/<launch>-handoff.json "<direction>"
   ```

   Omit the second argument when there is no direction. Use argument-safe tool
   calls or proper shell quoting. When sandbox restrictions are known, request
   scoped harness approval for this exact command before its first invocation.
   On a sandbox failure, report the checkpoint and escalate the same command.
   Other failures require explicit retry direction; the companion reconciles
   checkpoints. Preserve ambiguous prompt submissions for inspection.

Record each outcome before proceeding: launched, already-launched,
claimed-but-not-launched, or blocked-before-claim. Continue independent eligible
items after an item-specific failure; stop the remaining batch on a shared
infrastructure failure. Keep all successful workers and receipts intact.

**Complete when** every selected issue has a result and any partial claim has
its exact checkpoint and recovery action. Successful launch requires JSON
`ok: true` and `checkpoint: prompted`; `result: already-launched` confirms an
existing worker without a new prompt.

## 3. Hand back and stop

AFK workers run `/tengella-deliver` to Review or a blocker. HITL/Human workers
set up and wait. Extra direction preserves the mode. The companion supplies
one stop notification. Do not poll workers after prompt acceptance.

For each issue, show a clickable issue number **and the full plain URL**:

```text
[#5421](https://dev.azure.com/tengella/Tengella/_workitems/edit/5421)
https://dev.azure.com/tengella/Tengella/_workitems/edit/5421
```

Report organization/project/repository, result, mode, base branch/SHA, branch,
worktree, Herdr workspace/tab/pane, agent name, worker profile and receipt path.
Use a compact table for batch results, followed by URLs and receipt locations.
State launch acceptance separately from delivery completion. Include
`/close-issue <id>` and the receipt path for each successful launch.

`/close-issue` invokes `/tengella-finish` and retires only accepted, landed,
launch-owned resources from a surviving orchestrator. Launch leaves those
resources available for verification. An approved scope amendment belongs in
Boards and explicit direction to the existing worker; preserve the original
handoff. Repeating launch only reports the existing delivery.

**Complete when** the human has links, outcomes, receipts and next actions for
all selected issues. End the turn.
