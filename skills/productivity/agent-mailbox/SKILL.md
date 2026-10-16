---
name: agent-mailbox
description: Exchange messages and files between the Linux host agent and the Windows VM agent through the shared mailbox. Use when Jesper asks to send, check, process, or clean up mail for the other agent, or to hand a build, patch, or check across the host/VM boundary.
---

# Agent mailbox

Read the mailbox's `AGENTS.md` and follow the section for the requested
operation; it is the protocol both agents share.

| Side    | Mailbox root                                   |
| ------- | ---------------------------------------------- |
| Linux   | `/home/jesper/Shared/windows-dev/agent-bridge` |
| Windows | `\\192.168.122.1\windows-dev\agent-bridge`     |

If the root or its `bin/mailbox.ps1` is unavailable, or access is denied,
report the blocker and stop: the mailbox is the only transport between the
agents.

## Maintaining the protocol

`bridge/` in this skill is the versioned source of the mailbox's `AGENTS.md`
and `bin/mailbox.ps1`. After changing either, deploy from the Linux host with
`scripts/agent-mailbox-sync.sh --sync` in the skills repository.
