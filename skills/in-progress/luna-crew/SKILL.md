---
name: luna-crew
description: Coordinate Luna workers when the user asks for Luna delegation. Keep decisions and final review with the orchestrator.
---

# Luna crew

Keep design and discussion with the orchestrator; give bounded implementation to Luna. Optimize the whole task's cost, including preparation, supervision and rework. For a tiny edit where dispatch would cost more than doing it, recommend handling it directly; honor an explicit request to use a worker.

## Brief and dispatch

Settle the outcome and important constraints, then let the worker investigate implementation details. Avoid having both agents explore the same code in depth.

Send a compact, self-contained task message containing:

- Goal, acceptance criteria and relevant entry points.
- Working directory, owned paths, existing edits to preserve and starting revision when applicable.
- Required checks and authority boundaries, including whether commits or external writes are allowed.
- Instructions to preserve concurrent work, make routine implementation decisions, and report blocking scope or architecture questions.
- Requested return: outcome, changed paths, checks/results and remaining gates in the final message.

Use the host harness's supported delegation interface, whether Codex, Claude, agy, pi or another host. Request the actual `gpt-6-luna` model with fresh task context; use medium reasoning effort where supported. Host-specific tool names and parameters belong to that interface, not this workflow. Confirm model selection from available launch metadata. If Luna cannot be selected, report the limitation; do not substitute another model or backend silently. If effort cannot be configured, disclose that and use the host's supported Luna setting.

Start with one worker. Add workers only for substantial independent tasks with disjoint ownership. Keep tightly coupled work with the same worker. Workers should return to the orchestrator for further delegation.

The task message and final reply are the default brief and handback. Use durable files only when resuming across sessions or the user/repository requires them; reuse existing task artifacts. For a file-based handoff, [WORKER.md](WORKER.md) provides the worker instructions. Keep scratch files outside the delivered changes.

## While it works

Let the worker own implementation and affected verification. Use completion notifications or the harness's blocking wait within host limits. Check status only to answer a user request or investigate a concrete stall; avoid repeated supervisory turns and parallel implementation of the same task.

## Review and finish

Inspect the complete task diff, including new files and relevant surrounding code, against the brief and pre-existing edits. Reuse the worker's passing checks while their inputs remain unchanged; verify missing, contradictory or stale evidence. Required repository gates still apply.

Send actionable findings together to the same worker. Review the correction and affected invariants. If the same problem survives a correction, diagnose the misunderstanding or take over that part rather than repeating the loop.

The orchestrator's review is the default. Add independent review only when the user or repository requires it, or a concrete risk justifies it; preserve any required review axes. This skill adds no separate testing, review or planning skill chain.

Finish with the outcome, verification and remaining gates. Stage, commit or publish only within the task's granted authority. Claim token savings only when measured across the whole run.
