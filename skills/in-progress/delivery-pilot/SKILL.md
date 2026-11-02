---
name: delivery-pilot
description: Experiment with model roles and agent-executed verification on one delivery.
disable-model-invocation: true
---

# Delivery pilot

An opt-in experiment in who does the work and when evidence is gathered. The
target repository and its delivery workflow own scope, authorization, lifecycle,
required reviews and completion gates.

## Select the run

1. Read the selected boundary and target guidance. For Tengella work, run the
   `/tengella-deliver` skill and use this pilot to assign its work; other targets
   use their established delivery process. Reuse guidance already read while it
   remains applicable; refresh changed instructions and required live state.
   Reconstruct existing work before starting. Record the exact boundary,
   starting revision, stopping point and actual role/model/effort choices in the
   normal delivery record. Timestamp start, preflight, decisive proof, first
   frozen review and handoff there, plus correction and encountered
   environment/authority block intervals.
   **Done when** the selected boundary passes its start gate and each execution
   responsibility has one owner; otherwise name the precise blocker.

2. Use the role choices below unless the user specifies others. The recommended
   starting session is Sol 6.1 medium. Inspect available launch metadata and
   state any mismatch once. A skill does not change its running parent model:
   retain the user's selected parent and record it, or let the user choose a new
   session. Do not launch a second orchestrator beneath an active parent.
   **Done when** actual models and settings are known, or the unavailable role
   is reported before its dependent work starts.

| Responsibility | Starting choice | Work owned |
| --- | --- | --- |
| Orchestration | `gpt-6.1-sol`, medium | Scope, authority, delegation, evidence reconciliation and handoff |
| Implementation | One `gpt-6-luna`, high | Code, affected tests, smoke checks and capture generation |
| Independent review | `gpt-6.1-sol`, medium | Required review axes and evidence assessment |
| Escalated judgment | `gpt-6-astra`, high | One unresolved consequential design or correctness question |

These are Codex experiment choices, not cross-harness aliases. For another
harness, record the user's chosen available models before delegation. Request
Fast/priority only when the harness exposes that control and it was requested;
report the actual setting rather than equating the two. An unavailable model
requires a named choice, not a silent substitute.

## Execute with short feedback loops

3. Delegate bounded implementation in fresh context. Include accepted criteria,
   ownership, starting revision, existing edits, required verification, authority
   and the stopping point. The worker preserves concurrent work and produces a
   checked, frozen handback: candidate, commands/results, exact evidence paths
   and remaining gates. After handback, the orchestrator owns the current
   delivery record; redispatch the worker only for implementation or
   verification work.
   Before coding, identify existing regression seams affected by changed callers,
   routing, transport and output. Run the smallest existing affected check in its
   required environment, including restore/build/test when applicable. For external
   work, run one bounded native read through the permitted interface. Diagnose
   unchanged environment failures
   before retrying; resolve capability gaps before dependent checks.
   **Done when** the verification plan covers changed behavior and its regression
   seams, and the execution paths work or their exact blockers are named.

4. Prove one complete behavior early. For an external change, test the assumption
   most likely to change the implementation or accepted contract as soon as the
   path works. A write transformation needs an authorized write and independent
   readback; existing-record reads and synthetic checks cannot prove that round
   trip. Prepare the exact payload, isolated resource, operation limits and stop
   condition before requesting missing authority. Preserve authentication and
   environment limits. Exercise confirmation and presentation together for
   transformed content, including supported boundary inputs. Exercise generated
   navigation or continuation through the real parser with controlled I/O.
   **Done when** observed behavior supports the accepted contract at the required
   boundary. While unresolved, keep dependent capture expansion, final
   review and CI pending with the exact proof/authority gap and owner named;
   continue independent work within the target workflow.

5. Stabilize behavior before expanding captures. Reuse passing results while
   their inputs remain unchanged. Use the existing harness and production
   composition/presenters with actual result envelopes. Read
   [verification ownership](references/verification.md) for check owners, capture
   selection and evidence accounting; execute agent-owned checks before handoff.
   **Done when** each required check has current evidence or a named gap, and
   remaining human actions contain only the work still requiring that person.

## Review and hand off

6. Give each required review axis the same compact packet: frozen candidate and
   complete diff, accepted contract, applicable standards, required PR context
   and evidence links. Use separate fresh contexts when the workflow requires
   them. Request findings or clear, candidate identity, evidence limits and
   remaining gates. Keep verification with the implementer and assessment with
   reviewers; add an execution agent only for substantial independent checks.
   Consolidate findings into one correction brief and refresh affected checks.
   The orchestrator may apply and read back an agreed factual PR-summary
   correction without redispatch when source, criteria and reviewed meaning are
   unchanged. Redispatch for changed deliverable content or acceptance criteria,
   substantive PR changes, disputed evidence, or target-required PR assessment.
   Reuse established immutable identity evidence while applicable; refresh
   required mutable state.
   **Done when** required reviews and checks are clear on the current candidate.

7. Escalate to a bounded Astra consultation when scope/architecture has a
   consequential unresolved tradeoff, reviewers disagree on a correctness claim,
   or the same substantive defect survives a correction. Supply the question,
   relevant code/evidence and competing interpretations, not the session history.
   The orchestrator applies the decision and keeps ownership. A required
   structural review follows repository policy; this pilot adds no routine extra
   review layer.
   **Done when** the disputed decision is settled or an exact human decision is
   named. Routine progress does not trigger escalation.

8. Complete the established delivery process in its required review, CI and
   publication order. Use completion notifications or supported blocking waits;
   prepare finalization payloads during CI. Before applying them, refresh
   required live state and human responses; preserve revision guards, readbacks
   and current-source CI verification. The orchestrator checks the complete
   candidate and reconciles revision, review, CI, tracker state and remaining
   acceptance in one current handback, linking frozen history instead of
   repeating past status. Keep status-only reconciliation with the orchestrator
   and reuse valid tests. Progress updates report changed facts, decisions or
   blockers while respecting host communication requirements.
   **Done when** the authorized stopping point is read back and the next action
   has an owner. This pilot does not grant landing or release authority.

9. Run `/agent-usage` at the handoff, ending the measurement window before the
   accounting work. Record actual models/effort/service controls, task size,
   elapsed time, correction rounds, escalations, evidence gaps and remaining
   human work. Use the recorded milestones/block intervals and CI start/end times;
   note overlapping useful work rather than summing waits or calling the residual
   active work. Use available counters only and report unavailable measurements.
   Keep usage metadata out of product changes.
   **Done when** the run is recorded or the missing accounting capability is
   explicit.

## Compare the experiment

Choose with the user whether the next run tests workflow changes or implementer
models. For the next workflow trial, recommend retaining Luna high and the other
recorded role settings; the user chooses the next session. For a later model
comparison, explicitly select Sol 6.1 medium as implementer and hold the workflow
and other roles steady. Compare similar scope and stopping points; report scope
and environment differences instead of attributing all gains to a model. Evaluate
elapsed time, corrections, missed defects, remaining human effort and usage by
model. Fewer tokens with weaker evidence is not an improvement. Promote this
pilot only by a separate user decision after observing its results.
