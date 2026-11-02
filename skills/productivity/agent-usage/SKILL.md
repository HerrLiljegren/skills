---
name: agent-usage
description: Token usage ledger for agent runs in Claude Code or Codex. Use when the user asks to record what a run, delivery or delegation setup cost in tokens, or to compare runs by model, role or harness.
---

# Agent usage

Record each run's token usage from local transcripts into one ledger, then
compare runs. The ledger is `~/.local/share/agent-usage/runs.jsonl`
(override with `AGENT_USAGE_LEDGER`). It holds counts, models, timestamps and
subagent descriptions only, never message content.

`scripts/usage.py` reads both harnesses:

- **Claude Code**: `~/.claude/projects/*/<session>.jsonl` plus that session's
  `subagents/agent-*.jsonl`. The current session id is the transcript file name.
- **Codex**: `~/.codex/sessions/YYYY/MM/DD/rollout-*-<id>.jsonl` plus every
  descendant rollout (subagents and guardian approval reviews) linked by
  `parent_thread_id`.

## Record a run

1. Find the session and the run's **window**: UTC timestamps bounding the run
   inside the session. A session often holds several runs or unrelated chatter;
   take boundaries from the user-message timestamps in the transcript. Done
   when every thread that belongs to the run starts inside the window and the
   neighbouring work starts outside it.
2. Preview with `extract`, mapping subagent descriptions to roles. A
   `--role substring=role` mapping is case-insensitive and the first match
   wins, so list the specific ones first. The main thread defaults to
   `orchestrator` and any other thread to `subagent`:

   ```sh
   python3 scripts/usage.py extract <session> --harness claude|codex \
     --since <utc> --until <utc> \
     --role Finish=implementer --role Implement=implementer --role review=reviewer
   ```

   Done when every thread has the intended role and none is left as
   `subagent` by accident.
3. Run `record` with the same arguments plus the context a later comparison
   needs: what was delivered, how big it was, how it ended, and the setup
   (models per role, review rounds, stalls, compactions, CI detours):

   ```sh
   python3 scripts/usage.py record ... --label "<repo>#<id> <stage>" \
     --task "<one line>" --size "<files, lines, PR>" \
     --outcome "<landed, stalled, rework>" --notes "<setup per role>"
   ```

   Done when `record` prints the run's role table.

## Compare runs

```sh
python3 scripts/usage.py compare [--label <substring>]...
```

This prints a role table per run and a totals-by-model table. When reporting:

- Compare runs of similar size and stage, and name the differences
  (task size, review rounds, rework) beside the numbers.
- **Cache read** is the largest column but costs much less per token than cache
  write, uncached input or output. Weigh a model's output and cache write first.
- Usage limits weigh model tiers differently, so state the
  totals per model instead of summing across models.
- Codex `input_tokens` includes cached input; the script stores the
  uncached remainder so both harnesses share columns. Reasoning tokens are
  part of output.
