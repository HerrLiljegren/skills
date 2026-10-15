#!/usr/bin/env bash
# Open a Herdr review tab: a Codex reviewer on the left, a Hunk diff on the right.
#   launch.sh <pr-number | branch | worktree-path> [--model ID] [--effort low|medium|high]
# Prints key=value lines describing the session on success.
set -euo pipefail

MODEL=gpt-6.1-sol
EFFORT=low
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

die() { printf 'pr-walkthrough: %s\n' "$*" >&2; exit "${2:-1}"; }

test "${HERDR_ENV:-}" = 1 || die "not inside a Herdr pane (HERDR_ENV != 1)"
for c in jq git wt hunk herdr; do command -v "$c" >/dev/null || die "$c is required"; done

target=${1:?usage: launch.sh <pr-number|branch|worktree-path> [--model ID] [--effort LEVEL]}; shift
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL=${2:?model required}; shift 2 ;;
    --effort)
      EFFORT=${2:?effort required}
      case "$EFFORT" in low|medium|high) ;; *) die "invalid effort: $EFFORT" ;; esac
      shift 2 ;;
    *) die "unknown option $1" ;;
  esac
done

repo=$(git rev-parse --show-toplevel 2>/dev/null) || die "run from inside the repository to review"

# Returns the worktree path that has $1 checked out, or nothing.
worktree_for() { wt -C "$repo" list --format json | jq -r --arg b "$1" '.items[] | select(.branch == $b and .worktree != null) | .worktree.path' | head -n1; }

pr=""
if [[ $target =~ ^[0-9]+$ ]]; then
  pr=$target
  command -v az >/dev/null || die "az is required to resolve a PR number"
  # PR reads must not require command-log writes to the Azure config directory.
  info=$(cd "$repo" && AZURE_LOGGING_ENABLE_LOG_FILE=false az repos pr show --id "$pr" --query '{source:sourceRefName,target:targetRefName,title:title,status:status,repository:repository}' -o json) \
    || die "could not read PR $pr from Azure DevOps"
  repository_name=$(jq -er '.repository.name | strings | select(length > 0)' <<<"$info") \
    || die "PR $pr is missing repository identity"
  origin=$(git -C "$repo" remote get-url origin) || die "local repository has no origin"
  # PR numbers resolve across repositories; branch names alone cannot identify one.
  if ! jq -e --arg origin "$origin" '
    def canonical: ascii_downcase | sub("^https://[^/@]+@"; "https://")
      | sub("/+$"; "") | sub("\\.git$"; "");
    [.repository.sshUrl, .repository.remoteUrl]
    | any(.[]; type == "string" and (canonical == ($origin | canonical)))
  ' <<<"$info" >/dev/null; then
    die "PR $pr belongs to $repository_name; local origin does not match. Run from that repository checkout."
  fi
  branch=$(jq -r '.source | sub("^refs/heads/"; "")' <<<"$info")
  base_branch=$(jq -r '.target | sub("^refs/heads/"; "")' <<<"$info")
  title=$(jq -r '.title' <<<"$info")
elif [ -d "$target" ]; then
  branch=$(git -C "$target" branch --show-current)
  [ -n "$branch" ] || die "worktree at $target has a detached HEAD"
  base_branch=$(wt -C "$repo" list --format json | jq -er '.repo.default_branch')
  title=$branch
else
  branch=$target
  base_branch=$(wt -C "$repo" list --format json | jq -er '.repo.default_branch')
  title=$branch
fi

git -C "$repo" fetch --quiet origin "$base_branch" || die "could not fetch origin/$base_branch"
git -C "$repo" fetch --quiet origin "$branch" 2>/dev/null || [ -z "$pr" ] || die "could not fetch origin/$branch"

wt_path=$(worktree_for "$branch")
if [ -z "$wt_path" ]; then
  wt -C "$repo" switch "$branch" --no-cd --yes >/dev/null || die "wt could not create a worktree for $branch"
  wt_path=$(worktree_for "$branch")
  [ -n "$wt_path" ] || die "wt created no worktree for $branch"
fi

# A PR is reviewed as Azure DevOps shows it: the pushed head against the target's
# merge base. A local branch is reviewed with its uncommitted work included.
if [ -n "$pr" ]; then
  head_ref=origin/$branch
  diff_args="origin/$base_branch...origin/$branch"
  [ "$(git -C "$wt_path" rev-parse HEAD)" = "$(git -C "$wt_path" rev-parse "$head_ref")" ] && head_matches=true || head_matches=false
else
  head_ref=WORKTREE
  diff_args=$(git -C "$wt_path" merge-base "origin/$base_branch" HEAD)
  head_matches=true
fi

slug=$(printf '%s' "${pr:-$branch}" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9\n' '-' | sed 's/^-*//; s/-*$//')
name=$(printf 'review-%s' "$slug" | cut -c1-32)
herdr agent get "$name" >/dev/null 2>&1 && die "a reviewer named $name is already running; close its tab first"

tab=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$wt_path" --label "review ${pr:+#}${pr:-$branch}" --no-focus)
tab_id=$(jq -er '.result.tab.tab_id' <<<"$tab")
agent_pane=$(jq -er '.result.root_pane.pane_id' <<<"$tab")
hunk_pane=$(herdr pane split --pane "$agent_pane" --direction right --cwd "$wt_path" --no-focus | jq -er '.result.pane.pane_id')

herdr pane run "$hunk_pane" "hunk diff $diff_args" >/dev/null
session=""
for _ in $(seq 1 40); do
  session=$(hunk session list --json | jq -r --arg p "$wt_path" '.sessions[] | select(.repoRoot == $p) | .sessionId' | head -n1)
  [ -n "$session" ] && break
  sleep 0.5
done
[ -n "$session" ] || die "Hunk session did not register for $wt_path (see pane $hunk_pane)"

# The reviewer needs localhost for the Hunk daemon and network for az.
out=$(herdr agent start "$name" --kind codex --pane "$agent_pane" --timeout 60000 -- \
  -m "$MODEL" -c "model_reasoning_effort=$EFFORT" \
  -c sandbox_workspace_write.network_access=true 2>&1) \
  || die "Codex ($MODEL, $EFFORT) did not start: $out"

prompt="Read $HERE/REVIEWER.md and follow it. Review: ${pr:+PR $pr, }\"$title\". Branch: $branch. Base: $base_branch. Head: $head_ref (worktree HEAD matches: $head_matches). Hunk session: $session."
herdr agent prompt "$name" "$prompt" --wait --until working --timeout 15000 >/dev/null
herdr tab focus "$tab_id" >/dev/null

printf 'tab=%s\nreviewer=%s\nagent_pane=%s\nhunk_pane=%s\nhunk_session=%s\nworktree=%s\ndiff=%s\nmodel=%s/%s\n' \
  "$tab_id" "$name" "$agent_pane" "$hunk_pane" "$session" "$wt_path" "$diff_args" "$MODEL" "$EFFORT"
