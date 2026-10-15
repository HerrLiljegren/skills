---
name: close-issue
description: Finish a launched issue and retire its owned worktree and Herdr workspace.
disable-model-invocation: true
---

# Close Issue

The personal counterpart to `/launch-issue`. Run from a surviving orchestrator
outside the issue worktree and Herdr workspace. Invocation authorizes finishing
the selected issue under its existing landing contract and removing its clean,
landed launch-owned local resources. It does not authorize discarding changes,
force-removal, remote branch deletion, or closing unrelated work.

## Resolve

Accept an issue number or an explicit launch state path. Read host/repository
guidance and locate the launch receipt using the launch script's current state
location. Match exactly one receipt by issue and verified repository identity;
never derive a path from today's issue title. Read its immutable handoff and
record the issue URL, repository/remote, branch, worktree, agent and Herdr
workspace/tab/pane IDs. Confirm those identities against live metadata.

A receipt is evidence of identity, not authority to remove arbitrary paths.
Verify the worktree is a linked checkout of that repository, on the recorded
branch, and the workspace identifies that checkout. If launch reused an existing
workspace/worktree, require evidence it belongs exclusively to this issue.
Missing or ambiguous launch evidence blocks cleanup; finish can still proceed
for an unambiguously selected issue. Report cleanup as unavailable rather than
inventing resource identities.

Use the `/herdr` skill for live UI/process operations and installed Worktrunk
help for worktree operations. Before any removal, prove the orchestrator's
actual worktree and Herdr workspace differ from the target. If they do not,
return a handoff to a surviving orchestrator; never remove your own environment.

## Finish

Run `/tengella-finish` for the selected issue. It owns acceptance, authorized
landing, tracker transitions and their readback. Preserve its blockers; Review
or a green PR alone never authorizes cleanup. Do not repeat its verification or
merge again when it reports already-landed work.

Proceed when finish proves the issue's accepted outcome, target containment and
terminal state with no remaining gate requiring this workspace. Retain its
issue/PR links and final revision outside the worktree before retiring it.

## Retire owned resources

1. Fetch the agreed target and verify it contains the delivered source HEAD.
   For squash/rebase landing, use the finish evidence tying the exact reviewed
   tree to the landed result; a terminal tracker state alone is insufficient.
2. Inspect staged, unstaged and untracked files, including ignored local files
   that could hold user work. Preserve anything not proven disposable build
   output. Confirm no other worktree, branch or active task relies on removal.
3. Re-read the exact Herdr IDs and their current occupants. The issue worker must
   be idle/done with its handoff recorded; blocked, working or unknown status
   stops cleanup. Preserve any unrelated pane, tab, process or agent. Close the
   entire workspace only if all its contents belong to this launch; otherwise
   stop and report the overlap.
4. From the surviving orchestrator, stop the completed issue worker using the
   supported Herdr interface, then remove the exact worktree through Worktrunk
   without force. Remove its local branch only when landed and unused. Do not
   run `wt merge`: landing has already happened. If hooks or checks fail, stop
   with the remaining resources intact; do not bypass them.
5. Revalidate and close the owned Herdr workspace. Read back absence of the
   worktree/local branch and workspace. Report partial cleanup precisely; on
   retry inspect what remains rather than replaying successful actions.

Keep the launch receipt for provenance and save a small adjacent closeout
receipt with issue/PR links, landed revision, resource IDs and observed cleanup
results. Do not mark cleanup complete merely because commands returned success.

Return the issue link, final state/revision and removed or retained resources.
No extra approval ceremony is needed within this explicit invocation's scope;
new destructive effects or ambiguous ownership require a decision.
