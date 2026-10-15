#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage:
  worktree-space.sh <issue-number> "<issue title>"
  worktree-space.sh "<worktree name>"

Creates a Worktrunk-managed worktree and, inside herdr, opens a matching linked
worktree space without focusing it.
USAGE
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

slugify() {
  printf '%s' "$1" \
    | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

require_cmd git
require_cmd wt
require_cmd jq
require_cmd iconv

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

issue=""
name=""

if [[ "$1" =~ ^[0-9]+$ ]]; then
  issue="$1"
  shift
  [[ $# -gt 0 ]] || die "issue mode requires a title"
  name="$*"
else
  name="$*"
fi

slug="$(slugify "$name")"
[[ -n "$slug" ]] || die "could not derive a slug from: $name"

if [[ -n "$issue" ]]; then
  branch="issue/${issue}-${slug}"
  label="#${issue} ${slug//-/ }"
else
  branch="feature/${slug}"
  label="${slug//-/ }"
fi

common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"

if [[ "$(basename "$common_dir")" != ".git" ]]; then
  die "cannot resolve parent repo from git common dir: $common_dir"
fi

parent_repo="$(dirname "$common_dir")"
if [[ ! -d "$parent_repo/.git" ]]; then
  die "resolved parent repo does not look like a non-bare checkout: $parent_repo"
fi

checkout_path="$(
  git -C "$parent_repo" worktree list --porcelain \
    | awk -v wanted="refs/heads/${branch}" '
        /^worktree / { path = substr($0, 10) }
        /^branch / && substr($0, 8) == wanted { print path; found = 1; exit }
        END { if (!found) exit 1 }
      '
)" || checkout_path=""

created="false"
if [[ -z "$checkout_path" ]]; then
  wt_output="$(cd "$parent_repo" && wt new "$branch" 2>&1)" || {
    printf '%s\n' "$wt_output" >&2
    die "wt new failed for branch: $branch"
  }
  created="true"

  checkout_path="$(
    git -C "$parent_repo" worktree list --porcelain \
      | awk -v wanted="refs/heads/${branch}" '
          /^worktree / { path = substr($0, 10) }
          /^branch / && substr($0, 8) == wanted { print path; found = 1; exit }
          END { if (!found) exit 1 }
        '
  )" || die "worktree was created but checkout path could not be resolved for: $branch"
fi

already_open="null"
herdr_skipped="false"
herdr_workspace_id=""

if [[ "${HERDR_ENV:-}" == "1" ]]; then
  require_cmd herdr

  open_json="$(
    herdr worktree open \
      --cwd "$parent_repo" \
      --path "$checkout_path" \
      --label "$label" \
      --no-focus
  )"

  already_open="$(jq -r '.result.already_open' <<<"$open_json")"
  herdr_workspace_id="$(jq -r '.result.workspace.workspace_id // empty' <<<"$open_json")"

  herdr workspace list \
    | jq -e \
      --arg path "$checkout_path" \
      --arg repo "$parent_repo" \
      '.result.workspaces[]
       | select(.worktree.checkout_path == $path)
       | select(.worktree.is_linked_worktree == true)
       | select(.worktree.repo_root == $repo)' >/dev/null \
    || die "herdr workspace verification failed for checkout: $checkout_path"
else
  herdr_skipped="true"
fi

jq -n \
  --arg branch "$branch" \
  --arg checkout_path "$checkout_path" \
  --arg label "$label" \
  --argjson already_open "$already_open" \
  --argjson created "$created" \
  --argjson herdr_skipped "$herdr_skipped" \
  --arg herdr_workspace_id "$herdr_workspace_id" \
  --arg parent_repo "$parent_repo" \
  '{
    branch: $branch,
    checkout_path: $checkout_path,
    label: $label,
    already_open: $already_open,
    created: $created,
    herdr_skipped: $herdr_skipped,
    herdr_workspace_id: $herdr_workspace_id,
    parent_repo: $parent_repo
  }'
