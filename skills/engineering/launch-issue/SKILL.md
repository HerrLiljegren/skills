---
name: launch-issue
description: Launch an Azure DevOps Issue or Bug from any Tengella organization repository.
disable-model-invocation: true
---

# Launch Issue

Launch one Issue or Bug into a Herdr worker. Supply its number and optional direction:

```text
/launch-issue 5421
/launch-issue 5421 "focus on the Linux report-rendering seam"
```

The orchestrator resolves and claims the issue, writes an immutable handoff,
and invokes the companion script. The script owns worktree, workspace, worker,
and prompt submission. Launch ends when Herdr accepts the prompt; delivery
continues in the worker.

Requires Herdr, Worktrunk, a Codex or Pi worker, and the installed Tengella
workflow skills. This personal launcher uses the target repository’s tracker
contract.

## 1. Resolve and fetch

Run `/tengella-workflow` for target routing, authority, and lifecycle gates.
Resolve the tracker identity before fetching the work item:

1. require organization `tengella`;
2. read the root `AGENTS.md` and `docs/agents/issue-tracker.md` unless the
   harness already supplied them;
3. resolve the project, repository name, and repository remote from that
   repo-local tracker contract; and
4. require the exact `origin` remote and Azure DevOps repository lookup to
   match all three values.

Stop when any value is missing or mismatched. Do not infer a project from the
work-item number, probe other projects, or fall back to project `Tengella`.
Always pass the resolved project explicitly to Azure DevOps operations.

Fetch the complete work item once from that project. Read its type, title,
description, acceptance criteria, implementation and verification notes, state,
assignee, `Custom.AgentMode`, relations, URL, and repository links. Retain that
response for the handoff; later claim reads replace only state and assignee.
Reuse this snapshot during launch; the delivery worker refreshes lifecycle
and dependency evidence under `/tengella-deliver`.

When the item already has an assignee, prove that it is the current user with
an exact project-scoped query for this work-item ID and `AssignedTo = @Me`.
Do not list the user's assigned backlog. When assignment must change, require a
canonical current-identity result; stop if the connector cannot provide one.

Continue only for a supported `Issue` or `Bug` whose repository matches the
checkout and whose criteria and notes change no other repository, when
current-user identity is known, assignee and state do not conflict, and
`Custom.AgentMode` is exactly `AFK`, `HITL`, or `Human`. For an item that spans
repositories, report that it needs one Issue/Bug per repository and stop before
claiming. Default the immutable launch base to the current branch and `HEAD`.
When the user requests another base, resolve that branch to a full commit SHA
instead. For a latest remote branch, use `git ls-remote` against the verified `origin` and require exactly
one matching ref. Require the pinned commit to exist locally before claiming;
stop if it is unavailable. Record the selected branch and SHA in the handoff
without switching or modifying the invoking checkout.

Before claiming, verify `git`, `wt`, `jq`, `iconv`, `herdr`, the selected
worker executable, `HERDR_ENV=1`, and the current Herdr workspace ID. Verify
Herdr repository resolution with:

```sh
herdr worktree list --cwd "<verified repository root>"
```

Require the returned `source.repo_root` to match the verified repository root.
Stop before tracker mutation if this check fails. The caller's
`HERDR_WORKSPACE_ID` identifies its UI workspace; it may belong to another
repository. The handoff repository root is the source of truth for repository
operations. The companion opens worktrees with `--cwd` using that root.

**Complete when** the issue, repository, base SHA, worker profile, and local
preconditions are verified.

## 2. Claim only when needed

Evaluate the shared Ready gate and current dependency evidence before
claiming. Verify that the proposed claim satisfies In Progress, including
assignment to the triggering human. AFK alone does not establish readiness.
Stop with the exact gap if the claim cannot satisfy these gates.

Resolve the implementation state from the repo-local tracker contract and the
work item's live type metadata and transitions in the resolved project. The
target must be the documented implementation state, reachable from the current
state, non-terminal, and assigned to the current user. Stop if the repo-local
contract and live metadata disagree; do not substitute a state from another
project.

Re-read immediately before a tracker write. When state and assignee already
match, perform zero mutations. Otherwise update only the differing fields in
one canonical Azure DevOps operation, then re-read once and require the exact
result. Stop on a conflicting owner or terminal state; local launch artifacts
do not authorize tracker repair or rollback.

**Complete when** the verified tracker read matches the implementation state
and current-user assignment.

## 3. Write the handoff

Write one redacted JSON handoff under `/tmp`. Build it once from the retained
work-item response plus the verified post-claim state and assignee. Preserve
Markdown and include:

```json
{
  "id": 5421,
  "url": "...",
  "type": "Bug",
  "title": "...",
  "state": "Active",
  "assignee": { "id": "...", "displayName": "..." },
  "agentMode": "HITL",
  "description": "...",
  "acceptanceCriteria": "...",
  "implementationNotes": "...",
  "verificationNotes": "...",
  "relations": [],
  "worker": {
    "kind": "codex",
    "model": "gpt-6.1-sol",
    "reasoning": "medium"
  },
  "repository": {
    "organization": "tengella",
    "project": "...",
    "name": "...",
    "remote": "...",
    "root": "...",
    "baseBranch": "...",
    "baseCommit": "..."
  }
}
```

Default to the worker profile above. When the user explicitly requests Pi,
record `kind: "pi"` plus the exact provider/model and reasoning level; for
example `opencode-go/gpt-5.6-luna` and `high`. Support only `codex` and `pi`.
Resolve this profile during preflight, before claiming.

Write the handoff only after the claim readback so its state and assignee are
the verified post-claim values. Reuse an existing handoff only when its issue,
organization, project, repository name, remote, root, base commit, agent mode,
and worker profile exactly match. Exclude credentials and authentication
state; issue text may discuss those concepts. Preserve only task-relevant data. Write atomically
and make the completed file read-only.

**Complete when** the immutable file matches the schema and verified claim,
repository, base, mode, and worker profile.

## 4. Launch or resume

Run the companion once per authorized attempt from the repository root:

```sh
<installed skill directory>/scripts/launch-worktree.sh /tmp/<launch>-handoff.json
<installed skill directory>/scripts/launch-worktree.sh /tmp/<launch>-handoff.json "<extra direction>"
```

The script owns checkpoint reconciliation and preserves the invoking checkout.
Matching partial launches resume; conflicts and ambiguous prompt submissions
stop. Use its JSON result as evidence rather than replaying individual steps.

When the harness permission profile already shows that Worktrunk or Herdr
process control is restricted, request narrowly scoped approval before the
first companion invocation. Otherwise run normally; if sandbox restrictions
then block Worktrunk, report the exact checkpoint and request approval to rerun
the same command outside the sandbox. For any other failure, report the partial
state and wait for explicit retry approval. After approval, rerun the same
command and let checkpoint reconciliation own recovery; do not manually replay
an individual local step.

For `Custom.AgentMode = AFK`, the worker runs `/tengella-deliver` to its
human-ready Review handoff or a blocker. `HITL` and `Human` set up and wait for
direction. Extra direction preserves that mode. `/tengella-finish` owns later
landing and closeout under human authority. The script supplies the worker's
Herdr stop notification; existing workers keep their original prompt.

**Complete when** stdout is valid JSON with `ok: true` and
`checkpoint: prompted`. Report the issue link, organization/project/repository,
branch, worktree, Herdr workspace/tab/pane and agent name, worker profile,
prompt mode, and state path. Then end the turn. Prompt acceptance proves
launch only; worker completion is reported by its notification and handoff.
Keep handoff contents and session history out of output; do not poll the worker.

## End the loop

Include `/close-issue <id>` and the launch state path in the launch handoff to
the human. Delivery stops at Review and retains the workspace for verification.
After acceptance, `/close-issue` runs `/tengella-finish` and then retires only
this launch's clean, landed worktree and Herdr workspace from a surviving
orchestrator. That invocation authorizes scoped cleanup; launch alone does not
trigger deletion. The personal wrappers own workspace lifecycle; Tengella skills
remain independent of Worktrunk and Herdr.
