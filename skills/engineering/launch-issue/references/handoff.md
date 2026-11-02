# Handoff and receipt

Write one redacted JSON handoff per issue under `/tmp`, after verified claim
readback. Write atomically and make the completed file read-only. Preserve
Markdown and task-relevant relations/comments. Exclude credentials,
authentication state and session history.

```json
{
  "id": 5421,
  "url": "https://dev.azure.com/tengella/Tengella/_workitems/edit/5421",
  "revision": 12,
  "type": "Issue",
  "title": "Example issue",
  "state": "In Progress",
  "assignee": { "id": "...", "displayName": "..." },
  "agentMode": "AFK",
  "description": "...",
  "acceptanceCriteria": "...",
  "implementationNotes": "...",
  "verificationNotes": "...",
  "relations": [],
  "comments": [],
  "worker": {
    "kind": "codex",
    "model": "gpt-6.1-sol",
    "reasoning": "medium"
  },
  "repository": {
    "organization": "tengella",
    "project": "Tengella",
    "name": "Cli",
    "remote": "git@ssh.dev.azure.com:v3/tengella/Tengella/Cli",
    "root": "...",
    "baseBranch": "master",
    "baseCommit": "..."
  }
}
```

Use the actual post-claim revision and the verified item URL. Keep `url` as a
plain string; the companion returns it as `issue_url`. Human reports render
both `[#5421](URL)` and a separate full plain URL for terminals without link
support. JSON consumers use the URL directly.

Resolve worker kind/model/reasoning before claiming. Supported kinds are
`codex` and `pi`; Pi needs an explicit provider/model. Supported reasoning values are `low`, `medium`, `high`, `xhigh` and `max`;
validate the chosen value before claiming. The companion enforces them too. Extra direction is task input, not authority to
change Agent Mode or deliver another issue.

A handoff named `<launch>-handoff.json` has receipt `<launch>-state.json` beside
it. Other `.json` names use `.state.json`. Find receipts by their stored issue,
organization/project/repository, exact remote and root, not the current title.
Require exactly one match and verify its recorded handoff hash. Reuse the
recorded base/profile for an existing delivery; report conflicting new inputs.
An incomplete launch also requires an exact scope/profile/base match before
resuming. Never rewrite an old handoff to force it to match fresh requirements.

The receipt is launch evidence, not current tracker state. `checkpoint: prompted`
with accepted submission permits subsequent worker commits and dirty files;
partial setup still requires its original clean base. The companion validates
live worktree/workspace/agent identity before returning `already-launched`,
without modifying the receipt or sending another prompt. Unknown submission
outcomes stop to prevent duplicate execution.

The handoff records the original authorized scope. Delivery refreshes evidence
under `/tengella-deliver`. A conflicting scope change needs reconciliation;
an explicit human-approved amendment may supersede affected scope fields.
Record its Boards revision and decision in the worker's delivery evidence while
retaining the original handoff. A repeat launch does not deliver amendments.
