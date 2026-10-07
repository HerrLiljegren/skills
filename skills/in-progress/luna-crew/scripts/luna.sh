#!/usr/bin/env bash
# Deterministic Herdr plumbing for Luna 6 workers.
#   luna.sh start <lane> <focus> [--model ID] [--effort low|medium|high] [--from PANE] [--direction right|down]
#   luna.sh rename <lane> <new-lane> <focus>
#   luna.sh brief <lane> <brief-path>
#   luna.sh wait <lane>...
set -euo pipefail

LUNA_MODEL=gpt-6-luna
LUNA_EFFORT=medium

die() { printf 'luna: %s\n' "$*" >&2; exit "${2:-1}"; }

# The pane label is what the user scans in Herdr: "<lane> · <focus>".
label() { herdr pane rename "$1" "$2 · $3" >/dev/null; }
test "${HERDR_ENV:-}" = 1 || die "not inside a Herdr pane (HERDR_ENV != 1)"
command -v jq >/dev/null || die "jq is required"

cmd=${1:-}; shift || true
case "$cmd" in
  start)
    name=${1:?lane required}; focus=${2:?focus required}; shift 2
    from=${HERDR_PANE_ID:?}; dir=right
    while [ $# -gt 0 ]; do
      case "$1" in
        --model) LUNA_MODEL=${2:?model required}; shift 2 ;;
        --effort)
          LUNA_EFFORT=${2:?effort required}
          case "$LUNA_EFFORT" in low|medium|high) ;; *) die "invalid effort: $LUNA_EFFORT" ;; esac
          shift 2 ;;
        --from) from=$2; shift 2 ;;
        --direction) dir=$2; shift 2 ;;
        *) die "unknown option $1" ;;
      esac
    done
    pane=$(herdr pane split --pane "$from" --direction "$dir" --cwd "$PWD" --no-focus | jq -er '.result.pane.pane_id')
    label "$pane" "$name" "$focus"
    roots=$(jq -cn --arg a "$HOME/.nuget/packages" --arg b "$HOME/.local/share/NuGet" '[$a,$b]')
    # Keep network and NuGet caches available for restore/builds inside the worker sandbox.
    out=$(herdr agent start "$name" --kind codex --pane "$pane" --timeout 60000 -- \
      -m "$LUNA_MODEL" -c sandbox_workspace_write.network_access=true \
      -c "sandbox_workspace_write.writable_roots=$roots" \
      -c "model_reasoning_effort=$LUNA_EFFORT" 2>&1) || true
    if jq -e '.error.code == "agent_not_ready"' >/dev/null 2>&1 <<<"$out"; then
      printf '%s\n' "worker startup screen ($name):" >&2
      screen=$(herdr agent read "$name" --source recent --lines 15 2>&1) || true
      printf '%s\n' "$screen" >&2
      printf '%s\t%s\tblocked-startup\n' "$name" "$pane"; exit 3
    fi
    jq -e '.result' >/dev/null 2>&1 <<<"$out" || die "agent start failed: $out"
    printf '%s\t%s\tready\n' "$name" "$pane"
    ;;
  rename)
    old=${1:?lane required}; new=${2:?new lane required}; focus=${3:?focus required}
    pane=$(herdr agent get "$old" | jq -er '.result.agent.pane_id')
    [ "$old" = "$new" ] || herdr agent rename "$old" "$new" >/dev/null
    label "$pane" "$new" "$focus"
    printf '%s\t%s\trenamed\n' "$new" "$pane"
    ;;
  brief)
    name=${1:?lane required}; brief=${2:?brief path required}
    test -f "$brief" || die "brief not found: $brief"
    brief=$(realpath "$brief")
    # --until working proves the worker picked the prompt up, so a later wait cannot
    # match the pre-prompt idle state.
    herdr agent prompt "$name" "Read $brief and follow it exactly." --wait --until working --timeout 15000 >/dev/null
    printf '%s\tworking\n' "$name"
    ;;
  wait)
    [ $# -gt 0 ] || die "wait needs at least one worker name"
    # Return as soon as any worker stops working (idle, done, or blocked).
    pids=()
    for n in "$@"; do
      ( s=$(herdr agent wait "$n" | jq -r '.result.agent.agent_status // "unknown"'); printf '%s\t%s\n' "$n" "$s" ) &
      pids+=($!)
    done
    wait -n
    kill "${pids[@]}" 2>/dev/null || true
    ;;
  *) die "usage: luna.sh start|rename|brief|wait ..." ;;
esac
