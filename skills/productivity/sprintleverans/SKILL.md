---
name: sprintleverans
description: Audit sprint activity and prepare Swedish Tengella Orders for sprint delivery.
disable-model-invocation: true
---

# Sprintleverans

Turn a bounded period of work into an auditable shortlist, then create or reconcile the approved
Tengella Orders through their requested delivery state.

## 1. Establish the boundary

Resolve the date window, work scope, source harnesses, deadline, and requested stage: shortlist,
create Orders, assign sprint, or mark developed. Default the audit to the last two weeks when no
dates are given; state the dates. Use Swedish for Order content and the user's conversation language
for updates.

Resolve the exact sprint number before assigning it. Delivery day may be the first day of the next
sprint; the currently active sprint is not sufficient evidence for retrospective work.

Completion: the audit boundary is stated; every external action has a clear requested scope. Ask
only for missing decisions and reuse authorization already given. Approval to create Orders does not
by itself authorize submission or marking them developed.

## 2. Reconstruct activity

Use the requested Codex and Claude session records as primary evidence, including investigations,
design, reviews, implementation and unfinished work. Locate available stores from the environment.
Filter messages by timestamp and actual user/assistant role; exclude injected instructions, memory
blocks, tool output and inherited/subagent duplication from activity counts. Summarize the work
without reproducing raw session history or credentials.

Use session summaries as leads, then corroborate consequential delivery claims with current Git or
tracker evidence where practical. Distinguish author, commit and merge dates; an old patch merged
this sprint is completion work, not necessarily new implementation.

For DevOps reads, follow the installed workspace interface policy and current CLI help. If a
restricted-shell read fails, test authorized host access before attributing the failure to DevOps.
Resolve the author identity using supported syntax rather than assuming an `@me` shorthand. Report
unresolved reads explicitly; do not silently change interfaces.

Group related activity by outcome, not by session or PR count. Separate merged, published, deployed,
locally verified and human-accepted evidence. Include unfinished work with its remaining boundary.

Completion: present a numbered shortlist with purpose, scope, evidence anchors and delivery boundary
for each candidate. The user selects, combines or excludes items before creation, unless that
selection is already explicit.

## 3. Prepare the approved Orders

Check existing Orders and any run-local ID mapping before creating duplicates. For each selected
item, prepare:

| Field                   | Content                                                                        |
| ----------------------- | ------------------------------------------------------------------------------ |
| Titel                   | Concise Swedish outcome or capability                                          |
| Vad vill kunden uppnå?  | Why the work matters                                                           |
| Lösningsförslag         | Scope, work-item/PR references, period and remaining boundaries                |
| Lösning                 | Readable overarching explanation of what the solution changes and how it helps |
| Implementationsdetaljer | Technical approach and verification details that support the overview          |

Write substantive prose in Lösning, not a generic sentence directing the reader elsewhere. Keep
uncertain deployment or acceptance claims explicit. If a field appears only after approval, populate
it when that stage is authorized. For internal development work, use UTV and the confirmed
requester. Leave billing, customer acceptance, complexity and developer assignment at their existing
values unless the task supplies those decisions.

Completion: every approved item has distinct Swedish content and a destination; existing Order
numbers are retained for updates.

## 4. Apply the requested stage

Use the user's chosen browser and identify the tab by title and URL. Follow the browser tool's
current documentation. Inspect UI state before actions; use supported UI operations for edits,
transitions and drag-and-drop.

The observed Tengella route is:

1. Create through Internal → Beställningar → Ny; save and record both Best.nr and the URL's OrderId.
   These are different identifiers.
2. When submission is authorized, use Skicka in beställning.
3. Open Granska and use Godkänn when advancing into the approved sprint workflow.
4. Prioritize the Order in the priority list, moving only the selected cards.
5. Set Släpps i sprint to the confirmed number and save.
6. Use Markera som tillagd i sprint.
7. When explicitly requested, use Markera som utvecklad.

Treat this route as navigation guidance; current controls and validation own the actual transition
requirements. Saving Släpps i sprint alone does not establish Ligger i sprint. The sprint transition
can create a linked DevOps UserStory: inspect and retain that link rather than separately creating
another work item.

Keep a run-local ledger of Order number, URL, last verified state and pending action. After a
timeout, alert or unchanged screen, read persisted state before retrying; a server-side transition
may already have completed. Inspect alerts with supported tools and avoid blind mutation retries.

Under a deadline, complete and verify bounded batches and report progress. If a gate blocks one
item, continue independent authorized items and report the exact blocker. An automatic approval
rejection must be explained; obtain any missing authorization before retrying the rejected action.

Completion: each requested transition has a visible success state or an explicit per-Order blocker.
Existing unrelated Orders and content remain intact.

## 5. Read back and hand off

Reload every affected Order and verify its number, title, type, requester, requested sprint,
workflow status and saved narrative fields. Check Lösning contains the intended overview, not merely
non-empty text. Do not claim developed from a click attempt or from a populated sprint field.

Return the Order links and verified final states, plus any remaining gates or deadline overrun. Keep
the relevant browser page open for the user.

Completion: every approved item is accounted for, with no uncertain writes reported as complete.
