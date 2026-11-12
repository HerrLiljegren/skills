# Personal Skills

Small, reusable skills for personal engineering and workflow tasks. Promoted skills are listed here;
experimental and retired work stays in its bucket.

## Repository checks

Run `bash scripts/check.sh` with Git, Bash, uv, Node 24+, jq and iconv on PATH. It discovers tracked
Python unittest suites, shell scripts for `bash -n`, and Node test suites (regular and
linked-checkout modes). Python suites use Sprintleverans's locked uv runtime, including its Markdown
parser, with `python -I`. The first run downloads a managed Python and packages; system Python is
unchanged. GitHub Actions runs the same entry point in [check.yml](.github/workflows/check.yml).

These are runtime and syntax checks. Changed skills still need the metadata validator and invocation
policy checks described in [AGENTS.md](AGENTS.md) and
[.agents/invocation.md](.agents/invocation.md).

## Engineering

### User-invoked

- [`close-issue`](./skills/engineering/close-issue/SKILL.md) — finish a launched issue and retire
  its owned workspace
- [`launch-issue`](./skills/engineering/launch-issue/SKILL.md) — launch a Tengella issue into a
  Worktrunk checkout and Herdr worker

- [`nightly-builds`](./skills/engineering/nightly-builds/SKILL.md) — check Tengella nightly builds
  and diagnose failures; silent when healthy
- [`primer`](./skills/engineering/primer/SKILL.md) — create a ready-to-paste prompt for continuing
  current technical work in a fresh agent session

### Model-invoked

- [`prune-branches`](./skills/engineering/prune-branches/SKILL.md) — delete merged PR branches and
  their worktrees, locally and on the remote

## Productivity

### User-invoked

- [`sprintleverans`](./skills/productivity/sprintleverans/SKILL.md) — audit sprint work and deliver
  Swedish Tengella Orders

### Model-invoked

- [`agent-mailbox`](./skills/productivity/agent-mailbox/SKILL.md) — exchange messages and files with
  the Windows VM agent
- [`agent-usage`](./skills/productivity/agent-usage/SKILL.md) — record and compare token usage of
  Claude Code and Codex runs
- [`codex-resets`](./skills/productivity/codex-resets/SKILL.md) — safely show available Codex reset
  credits
- [`vim-helper`](./skills/productivity/vim-helper/SKILL.md) — answer Vim, Neovim, and Zed Vim-mode
  questions using the real editor configuration
- [`where-were-we`](./skills/productivity/where-were-we/SKILL.md) — reconstruct interrupted work and
  identify the next useful step
- [`x-thread-resource`](./skills/productivity/x-thread-resource/SKILL.md) — parse X threads into
  source-grounded evidence
