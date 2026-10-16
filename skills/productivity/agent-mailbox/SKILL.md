---
name: agent-mailbox
description: Exchange messages and files with the Windows VM agent through the shared mailbox. Use when Jesper asks to send, check, process, or clean up mail for the Windows agent, or to hand a build, patch, or check to the Windows VM.
---

# Agent mailbox

The mailbox root is `/home/jesper/Shared/windows-dev/agent-bridge`. Read its
`AGENTS.md` and follow the section for the requested operation; it is the
protocol both agents share.

If the root or its `bin/mailbox.ps1` is unavailable, or access is denied,
report the blocker and stop: the mailbox is the only transport to the Windows
agent.

## Maintaining the protocol

`bridge/` in this skill is the versioned source of the mailbox's `AGENTS.md`
and `bin/mailbox.ps1`. After changing either, deploy with
`scripts/agent-mailbox-sync.sh --sync` from the skills repository.
