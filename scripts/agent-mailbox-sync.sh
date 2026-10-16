#!/usr/bin/env bash
set -euo pipefail

# The Windows agent reads the protocol and helper from the shared mailbox, which
# is not versioned; this skill's bridge/ directory is their source.
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source_root="$repo_root/skills/productivity/agent-mailbox/bridge"
mailbox_root="${AGENT_MAILBOX_ROOT:-$HOME/Shared/windows-dev/agent-bridge}"
files=(AGENTS.md bin/mailbox.ps1)
mode="${1:---check}"

case "$mode" in
  --check)
    drift=0
    for file in "${files[@]}"; do
      cmp --silent "$source_root/$file" "$mailbox_root/$file" || {
        printf 'agent-mailbox drift: %s\n' "$mailbox_root/$file" >&2
        drift=1
      }
    done
    [ "$drift" -eq 0 ] || exit 1
    printf 'agent-mailbox bridge: current\n'
    ;;
  --sync)
    [ -d "$mailbox_root" ] || {
      printf 'agent-mailbox root not found: %s\n' "$mailbox_root" >&2
      exit 1
    }
    for file in "${files[@]}"; do
      install -D -m 0644 -- "$source_root/$file" "$mailbox_root/$file"
      printf 'synced %s\n' "$mailbox_root/$file"
    done
    ;;
  *)
    printf 'usage: %s [--check|--sync]\n' "${0##*/}" >&2
    exit 2
    ;;
esac
