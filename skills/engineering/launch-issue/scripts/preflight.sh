#!/usr/bin/env bash
set -euo pipefail

# Local evidence only. The orchestrator separately checks live tracker gates.
if [[ $# != 5 ]]; then
  printf 'usage: %s <root> <organization> <project> <repository> <worker>\n' "$0" >&2
  exit 2
fi
command -v jq >/dev/null || { echo 'preflight requires jq to report JSON' >&2; exit 1; }
root="$1" organization="$2" project="$3" repository="$4" worker="$5"
errors=()
for required in git wt iconv herdr tengella "$worker"; do
  command -v "$required" >/dev/null || errors+=("Missing executable: $required")
done
[[ "$organization" == tengella ]] || errors+=('Organization must be tengella')
[[ -n "$project" && -n "$repository" ]] || errors+=('Project and repository are required')
[[ "$worker" == codex || "$worker" == pi ]] || errors+=('Worker must be codex or pi')
[[ "${HERDR_ENV:-}" == 1 ]] || errors+=('HERDR_ENV must be 1')
[[ -n "${HERDR_WORKSPACE_ID:-}" ]] || errors+=('Herdr caller workspace ID is missing')
repo_root='' remote='' base_branch='' base_commit=''
if command -v git >/dev/null; then
  if repo_root="$(git -C "$root" rev-parse --show-toplevel 2>/dev/null)"; then
    [[ "$repo_root" == "$root" ]] || errors+=('Root must be the exact repository top level')
    remote="$(git -C "$root" remote get-url origin 2>/dev/null)" || errors+=('Origin is missing')
    ssh="git@ssh.dev.azure.com:v3/${organization}/${project}/${repository}"
    https="https://dev.azure.com/${organization}/${project}/_git/${repository}"
    https_user="https://${organization}@dev.azure.com/${organization}/${project}/_git/${repository}"
    [[ "$remote" == "$ssh" || "$remote" == "$https" || "$remote" == "$https_user" ]] \
      || errors+=('Origin does not match the documented repository identity')
    base_branch="$(git -C "$root" symbolic-ref --quiet --short HEAD)" \
      || errors+=('Invoking checkout is detached')
    base_commit="$(git -C "$root" rev-parse 'HEAD^{commit}' 2>/dev/null)" \
      || errors+=('Invoking HEAD is not a commit')
  else
    errors+=('Repository root is unavailable')
  fi
fi
if command -v herdr >/dev/null && [[ "${HERDR_ENV:-}" == 1 && -n "$repo_root" ]]; then
  # Preserve the original permission diagnostic on stderr for scoped escalation.
  if herdr_json="$(herdr worktree list --cwd "$root")"; then
    common_dir="$(git -C "$root" rev-parse --path-format=absolute --git-common-dir)"
    if ! jq -e --arg root "$root" --arg key "$common_dir" \
      '.result.source.repo_key == $key and any(.result.worktrees[]; .path == $root)' \
      <<<"$herdr_json" >/dev/null 2>&1; then
      errors+=('Herdr repository resolution does not match the verified root')
    fi
  else
    errors+=('Herdr repository check failed; inspect stderr for access restrictions')
  fi
fi
errors_json='[]'
if (( ${#errors[@]} )); then
  errors_json="$(printf '%s\n' "${errors[@]}" | jq -R . | jq -s .)"
fi
jq -n --arg root "$repo_root" --arg branch "$base_branch" --arg commit "$base_commit" \
  --arg workspace "${HERDR_WORKSPACE_ID:-}" --arg worker "$worker" \
  --argjson errors "$errors_json" \
  '{ok: ($errors | length == 0), root: $root, base_branch: $branch,
    base_commit: $commit, caller_workspace: $workspace, worker: $worker,
    errors: $errors}'
(( ${#errors[@]} == 0 ))
