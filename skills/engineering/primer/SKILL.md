---
name: primer
description: Create a ready-to-paste primer for continuing current technical work in a fresh agent session.
disable-model-invocation: true
---

# Primer

Create a prompt addressed directly to a fresh coding agent. Transfer the
current technical state so the new session can continue the work without this
conversation.

## Workflow

1. Fix the continuation scope.
   - Treat any arguments as the next session's focus. Otherwise, use the
     current active goal and its stated scope.
   - Read the applicable agent instructions and identify the workspace,
     repository, branch, revision, and working-tree state.
   - Completion criterion: the intended outcome, active scope, and exact
     workspace are known or explicitly unresolved.

2. Establish the current state from evidence.
   - Inspect the relevant diff, recent commits, plans, specifications, ADRs,
     issues, tests, and implementation files available in the workspace.
   - Use the conversation for decisions or intent that the workspace does not
     preserve. Prefer current workspace evidence when it conflicts with an
     earlier conversational claim.
   - Record what was implemented, what was actually verified, important
     decisions and their rationale, constraints, failed approaches, gotchas,
     and unresolved work.
   - Keep inspection read-only. Treat earlier verification results as
     historical evidence and state their last known result.
   - Completion criterion: every material statement needed to resume is backed
     by current evidence or visibly marked unresolved.

3. Write the primer.
   - Address the next agent directly and focus on the project's current state,
     not how the conversation unfolded.
   - Use the output shape below. Omit empty optional details, but retain every
     section.
   - Reference authoritative plans, specifications, ADRs, issues, commits, and
     diffs by path or URL. Include the conclusion or consequence the next
     agent needs without reproducing the artifact.
   - Order next steps by dependency. Give every step an observable completion
     criterion, and make the first step the exact next move.
   - Include exact verification commands, what each command proves, and its
     last known result when available.
   - Completion criterion: a fresh agent can locate the work, understand the
     technical direction, perform the first action, and determine when it is
     complete without access to this conversation.

4. Audit the primer.
   - Account for the goal, implemented and verified work, decisions, working
     map, constraints, gotchas, unresolved work, next steps, and verification.
   - Keep only information that changes how the next agent should understand,
     execute, or verify the work.
   - Sanitize credentials, authentication state, session history, personal
     information, and sensitive data.
   - Mark inference and uncertainty explicitly. Preserve unrelated user
     changes and scope boundaries in the instructions to the next agent.
   - Completion criterion: all required sections are actionable, all claims
     have a clear evidence status, and the prompt contains no sensitive data.

Return only the finished primer unless the user asks for commentary or a file.

## Output Shape

```md
# Session primer

You are continuing technical work in `<workspace>`.

## Goal

<Concrete outcome and active scope.>

## Current state

- Repository and branch:
- Revision and working tree:
- Active implementation state:

## Implemented and verified

<Completed behavior plus the evidence that verifies it.>

## Technical decisions

<Important architectural and implementation decisions, with rationale and
consequences.>

## Working map

<Key files, components, issues, specifications, commits, and why each matters.>

## Constraints

<Instructions, conventions, compatibility requirements, scope boundaries, and
unrelated changes to preserve.>

## Known issues and unresolved work

<Gotchas, failed approaches, open questions, assumptions, and missing evidence.>

## Next steps

1. <Exact next action. Done when: observable completion criterion.>
2. <Following action. Done when: observable completion criterion.>

## Verification

- `<command>` — proves <behavior>; last known result: <result or not run>
```
