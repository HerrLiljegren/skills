---
name: triage
description: Turn a ticket, order, bug or idea into an AFK-ready issue.
disable-model-invocation: true
---

# Triage

Take one input (a Tengella Ticket or Order, an Azure DevOps item, a Linear issue, a bug report or a
loose idea) and turn it into an **AFK-ready** issue: one an agent can implement to green PRs without
asking anything.

The human is here for this stage. Ask through the harness's question tool (Claude Code:
`AskUserQuestion`; Codex: its user-input tool) so each question raises a notification. Batch related
questions; ask only what code, tickets and running the system cannot answer.

## 1. Gather

Read the input and everything it links. Then gather context from what is available: the repositories
involved, their `AGENTS.md`, related issues and PRs, logs and traces, the running system.

Record the **origin**: the Ticket or Order reference this work answers, if any. The origin decides
what "done" means at close.

## 2. Scope the repositories

Decide whether this is a single-repo or multi-repo issue. For multi-repo, name each repo's role and
the order: the **producer** (for example an API in `tengella_bare`) lands before the **consumer**
(for example the Android app in Mobilkvittens) can consume it.

## 3. Reproduce

If the input describes a defect, reproduce it. Use what the repo already has to run the system; an
Aspire AppHost is allowed and preferred where it exists. Capture the steps and the observed result.
If it cannot be reproduced, record what was tried and ask whether to continue.

## 4. Resolve

Turn every uncertainty into a decision: settle it from evidence, or ask. Done when no open question
remains that would make an AFK agent stop or guess.

## 5. Record the issue

Write the issue in Linear, team DEV (Engineering Lab), unless the user names another team. When the
input is already an Azure DevOps item in a Feature tree, keep the issue there and append to it
instead. Use these sections:

- **Origin**: Ticket/Order reference, or "none".
- **Problem**: what is wrong or missing, in the user's terms.
- **Repositories**: each repo, its role (producer/consumer) and landing order.
- **Reproduction**: steps and observed result, or why none applies.
- **Acceptance criteria**: each one checkable by running something or reading a diff, as `- [ ]`
  checkboxes. Mark a criterion that only a human can check as a human gate.
- **Authorizations**: what `/afk` may do without asking for this issue, such as running the local
  database harness, starting Aspire, queueing CI or commenting on the tracker. Ask the user for
  these here, so the AFK run does not have to.
- **Out of scope**: what was considered and deliberately left out.
- **Decisions**: the questions asked here and their answers.

Show rather than tell. Where it helps a reader, attach media: a screenshot of the defect, a chart of
the measured numbers, a diagram of the flow being changed. The `pr` skill's visuals section lists
the kinds and where each works.

Done when every acceptance criterion is checkable and the issue links its origin.

## 6. Hand off

Report the issue link. Then ask through the question tool whether to start `/afk` on it in a new
top-level session (in T3, a new thread), not in this one and not as a subagent. Start it only on a
yes, with the model and effort the user picks (recommended: the **afk** role from host-local agent
guidance).
