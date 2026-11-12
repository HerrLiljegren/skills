---
name: sprintleverans
description: Audit sprint activity and deliver Swedish Tengella Orders for sprint delivery.
disable-model-invocation: true
---

# Sprintleverans

Turn a sprint's work into presentation-ready Tengella Orders: collect, shortlist, author, deliver,
verify. The scripts beside this file do the mechanical work; your judgement goes into grouping and
writing. Run the scripts with `python3 -I <skill-dir>/scripts/<script>.py`.

## 1. Set up the pack

Resolve the sprint number, the target environment (production unless told otherwise) and the
requester. The sprint is the one the Orders belong to, which may differ from today's active sprint.
Create the pack folder and `manifest.json` as described in [PACK.md](PACK.md). Internal development
work defaults to UTV, `requireCustomerAccept: false` and `shouldBeInvoiced: false`; record these in
`choices` and name them in the shortlist so the user confirms them with the selection.

Completion: `manifest.json` names the sprint, period, environment, requester and choices.

## 2. Collect and shortlist

Run `collect.py --pack <pack> --sprint <N>`. It writes completed PRs from every repository, Codex
and Claude session leads, and screenshot leads for the sprint window into `<pack>/collect/`. Read T3
work with `t3_thread_list` (all projects, bounded) and `t3_thread_read` only for threads whose work
has no PR yet. Count a mirrored or subagent thread once, with its parent.

Group by outcome, not by PR or session: one Order per delivered capability or fix. Merged PRs are
the evidence for `done`; open PRs, prototypes and investigations are `wip`. Put each group in
`manifest.json` with an `orders/NN-slug/notes.md` holding its evidence links.

Completion: the user sees a numbered shortlist (title, one-line outcome, evidence, done/wip) and
selects, merges or drops items. Record their instruction verbatim in `manifest.authorization`,
together with the terminal stage they approved. Approval to create Orders authorizes only creation;
a later stage needs its own approval.

## 3. Author the Orders

Write each selected `order.json` following [FIELDS.md](FIELDS.md): Lösning is the slide the room
sees, so it carries the outcome. Choose screenshots from `collect/images.json`, copy them into
`images/` and give each a field and alt text; put the main one on Lösning.

Completion: `deliver.py check --pack <pack>` passes for every selected item, and you have read each
Lösning as the audience will see it.

## 4. Deliver

1. `deliver.py preflight --pack <pack>` resolves the CLI environment, write scope, UTV type,
   requester and sprint into `readiness.json` and lists Orders whose titles already exist. Resolve
   every duplicate: set `existingOrderId` to update that Order, or retitle.
2. `deliver.py run --pack <pack> --dry-run` prints every command. Check it against the approved
   stage.
3. `deliver.py run --pack <pack>` creates or updates each Order and takes it through the normal flow
   to its stage: create, submit, approve, prioritize, assign sprint, Lösning and
   Implementationsdetaljer, images, mark developed. Each step's operation ID goes to `ledger.json`
   before dispatch. One blocked item does not stop the others.

For a blocked item, inspect its retained operation with `tengella order operation --help` and
recover with that same ID; a new ID is a new write. Rerunning `run` resumes after the last verified
step and refuses any step whose outcome is uncertain.

Completion: `run` reports every selected item at its stage, or names its blocker.

## 5. Verify and hand back

Run `deliver.py verify --pack <pack>`. It reads back each Order and its linked DevOps story, and
writes `LEVERANS-<N>.md` with Present links. Open one Order's Present page in the user's browser to
check that Lösning and its image render well.

Completion: hand back the `LEVERANS-<N>.md` link, the count reached per stage, each blocker with its
operation ID, and any `wip` items presented without an Order.
