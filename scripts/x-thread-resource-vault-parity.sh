#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source_file="$repo_root/skills/productivity/x-thread-resource/scripts/read_x_thread.py"
vault_root="${KNOWLEDGE_VAULT_ROOT:-$HOME/knowledge}"
target_file="$vault_root/_system/agents/skills/x-thread-resource/scripts/read_x_thread.py"
mode="${1:---check}"

case "$mode" in
  --check)
    cmp --silent "$source_file" "$target_file" || {
      printf 'x-thread-resource parser drift: %s\n' "$target_file" >&2
      exit 1
    }
    printf 'x-thread-resource parser parity: current\n'
    ;;
  --sync)
    mkdir -p -- "$(dirname -- "$target_file")"
    install -m 0755 -- "$source_file" "$target_file"
    printf 'synced x-thread-resource parser to %s\n' "$target_file"
    ;;
  *)
    printf 'usage: %s [--check|--sync]\n' "${0##*/}" >&2
    exit 2
    ;;
esac
