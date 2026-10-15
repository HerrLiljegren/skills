#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'usage: %s <handoff.json> [start-prompt]\n' "$0" >&2
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

[[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
handoff="$1"
start_prompt="${2:-}"
[[ -f "$handoff" ]] || die "handoff does not exist: $handoff"

for command in git wt jq iconv herdr; do
  command -v "$command" >/dev/null || die "required command not found: $command"
done
[[ "${HERDR_ENV:-}" == 1 ]] || die 'launch must run inside Herdr (HERDR_ENV=1)'
[[ -n "${HERDR_WORKSPACE_ID:-}" ]] || die 'current Herdr workspace ID is unavailable'

handoff="$(realpath "$handoff")"
handoff_hash="$(git hash-object "$handoff")"
issue="$(jq -er '.id | tostring | select(test("^[0-9]+$"))' "$handoff")" \
  || die 'handoff has no numeric issue ID'
issue_type="$(jq -er '.type | select(. == "Issue" or . == "Bug")' "$handoff")" \
  || die 'handoff issue type must be Issue or Bug'
issue_state="$(jq -er '.state | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no issue state'
title="$(jq -er '.title | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no title'
agent_mode="$(jq -er '.agentMode | select(. == "AFK" or . == "HITL" or . == "Human")' "$handoff")" \
  || die 'handoff agent mode must be AFK, HITL, or Human'
agent_kind="$(jq -er '(.worker.kind // "codex") | select(. == "codex" or . == "pi")' "$handoff")" \
  || die 'handoff worker kind must be codex or pi'
organization="$(jq -er '.repository.organization | select(. == "tengella")' "$handoff")" \
  || die 'handoff repository organization must be tengella'
project="$(jq -er '.repository.project | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no repository project'
repository_name="$(jq -er '.repository.name | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no repository name'
repository_remote="$(jq -er '.repository.remote | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no repository remote'
expected_repo="$(jq -er '.repository.root | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no repository root'
base_revision_input="$(jq -er '.repository.baseCommit | select(type == "string" and length > 0)' "$handoff")" \
  || die 'handoff has no base commit'

slug="$({ printf '%s' "$title" | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || true; } \
  | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
[[ -n "$slug" ]] || die 'title produced an empty slug'
branch="issue/${issue}-${slug}"
agent_name="issue${issue}"
if [[ "$agent_kind" == codex ]]; then
  model="$(jq -er '.worker.model // "gpt-6.1-sol" | select(type == "string" and length > 0)' "$handoff")" \
    || die 'handoff has no Codex model'
  reasoning_effort="$(jq -er '.worker.reasoning // "medium" | select(. == "low" or . == "medium" or . == "high" or . == "xhigh" or . == "max")' "$handoff")" \
    || die 'handoff has an unsupported Codex reasoning level'
else
  model="$(jq -er '.worker.model | select(type == "string" and length > 0)' "$handoff")" \
    || die 'Pi worker requires an explicit provider/model'
  reasoning_effort="$(jq -er '.worker.reasoning | select(. == "low" or . == "medium" or . == "high" or . == "xhigh" or . == "max")' "$handoff")" \
    || die 'Pi worker requires a supported reasoning level'
fi
command -v "$agent_kind" >/dev/null || die "required worker command not found: $agent_kind"
prompt_mode='setup-only'
[[ "$agent_mode" == AFK ]] && prompt_mode='implement'

parent_repo="$(git rev-parse --show-toplevel)"
[[ "$(realpath "$parent_repo")" == "$(realpath "$expected_repo")" ]] \
  || die 'handoff repository does not match the current checkout'
actual_remote="$(git -C "$parent_repo" remote get-url origin)" \
  || die 'current checkout has no origin remote'
[[ "$actual_remote" == "$repository_remote" ]] \
  || die 'handoff repository remote does not match origin'
ssh_remote="git@ssh.dev.azure.com:v3/${organization}/${project}/${repository_name}"
https_remote="https://dev.azure.com/${organization}/${project}/_git/${repository_name}"
https_user_remote="https://${organization}@dev.azure.com/${organization}/${project}/_git/${repository_name}"
[[ "$repository_remote" == "$ssh_remote" || "$repository_remote" == "$https_remote" \
  || "$repository_remote" == "$https_user_remote" ]] \
  || die 'handoff project and repository do not match its Azure DevOps remote'
root_branch="$(git -C "$parent_repo" symbolic-ref --quiet --short HEAD)" \
  || die 'root checkout is detached'
root_head="$(git -C "$parent_repo" rev-parse HEAD)"
base_revision="$(git -C "$parent_repo" rev-parse "${base_revision_input}^{commit}")" \
  || die 'handoff base commit is not in the current repository'
[[ "$base_revision" == "$base_revision_input" ]] || die 'handoff base commit is not canonical'

case "$handoff" in
  *-handoff.json) state_path="${handoff%-handoff.json}-state.json" ;;
  *.json) state_path="${handoff%.json}.state.json" ;;
  *) die 'handoff path must end in .json' ;;
esac

checkpoint=claimed
worktree_path=''
herdr_workspace_id=''
herdr_tab_id=''
herdr_pane_id=''
worktree_resumed=false
workspace_resumed=false
agent_resumed=false
prompt_resumed=false
prompt_submission='not-started'
agent_status=''
recorded_rank=0

checkpoint_rank() {
  case "$1" in
    claimed) printf '1\n' ;;
    worktree-created) printf '2\n' ;;
    workspace-open) printf '3\n' ;;
    agent-ready) printf '4\n' ;;
    prompted) printf '5\n' ;;
    *) return 1 ;;
  esac
}

fail() {
  jq -n \
    --arg issue "$issue" --arg branch "$branch" --arg checkpoint "$checkpoint" \
    --arg error "$*" --arg handoff "$handoff" --arg state_path "$state_path" \
    --arg parent_repo "$parent_repo" --arg root_head "$root_head" \
    --arg base_revision "$base_revision" --arg worktree_path "$worktree_path" \
    --arg herdr_workspace_id "$herdr_workspace_id" --arg herdr_tab_id "$herdr_tab_id" \
    --arg herdr_pane_id "$herdr_pane_id" --arg agent_name "$agent_name" \
    --arg agent_kind "$agent_kind" --arg model "$model" \
    --arg reasoning_effort "$reasoning_effort" --arg prompt_submission "$prompt_submission" \
    '{ok: false, issue: $issue, branch: $branch, checkpoint: $checkpoint,
      handoff: $handoff, state_path: $state_path, parent_repo: $parent_repo,
      root_head: $root_head, base_revision: $base_revision,
      worktree_path: $worktree_path, herdr_workspace_id: $herdr_workspace_id,
      herdr_tab_id: $herdr_tab_id, herdr_pane_id: $herdr_pane_id,
      agent_name: $agent_name, agent_kind: $agent_kind, model: $model,
      reasoning_effort: $reasoning_effort, prompt_submission: $prompt_submission,
      error: $error}'
  exit 1
}

start_agent() {
  local attempt error_path
  error_path="$(mktemp)"
  for (( attempt = 1; attempt <= 50; attempt++ )); do
    if agent_json="$("${agent_start_command[@]}" 2>"$error_path")"; then
      rm "$error_path"
      return 0
    fi
    if ! jq -e '.error.code == "agent_pane_busy"' "$error_path" >/dev/null 2>&1; then
      cat "$error_path" >&2
      rm "$error_path"
      return 1
    fi
    if (( attempt == 50 )); then
      cat "$error_path" >&2
      rm "$error_path"
      return 1
    fi
    sleep 0.1
  done
}

write_state() {
  state_tmp="$(mktemp "${state_path}.XXXXXX")"
  jq -n \
    --arg issue "$issue" --arg issue_type "$issue_type" --arg issue_state "$issue_state" \
    --arg title "$title" --arg branch "$branch" --arg checkpoint "$checkpoint" \
    --arg handoff "$handoff" --arg handoff_hash "$handoff_hash" \
    --arg organization "$organization" --arg project "$project" \
    --arg repository_name "$repository_name" --arg repository_remote "$repository_remote" \
    --arg agent_mode "$agent_mode" \
    --arg state_path "$state_path" --arg parent_repo "$parent_repo" \
    --arg root_branch "$root_branch" --arg root_head "$root_head" \
    --arg base_revision "$base_revision" --arg worktree_path "$worktree_path" \
    --arg herdr_workspace_id "$herdr_workspace_id" --arg herdr_tab_id "$herdr_tab_id" \
    --arg herdr_pane_id "$herdr_pane_id" --arg agent_name "$agent_name" \
    --arg agent_kind "$agent_kind" --arg agent_status "$agent_status" --arg model "$model" \
    --arg reasoning_effort "$reasoning_effort" --arg prompt_mode "$prompt_mode" \
    --arg prompt_submission "$prompt_submission" \
    --argjson worktree_resumed "$worktree_resumed" \
    --argjson workspace_resumed "$workspace_resumed" \
    --argjson agent_resumed "$agent_resumed" \
    --argjson prompt_resumed "$prompt_resumed" \
    '{ok: true, checkpoint: $checkpoint, issue: $issue, issue_type: $issue_type,
      issue_state: $issue_state, title: $title, branch: $branch,
      organization: $organization, project: $project,
      repository_name: $repository_name, repository_remote: $repository_remote,
      agent_mode: $agent_mode,
      handoff: $handoff, handoff_hash: $handoff_hash, state_path: $state_path,
      parent_repo: $parent_repo, root_branch: $root_branch, root_head: $root_head,
      base_revision: $base_revision, worktree_path: $worktree_path,
      herdr_workspace_id: $herdr_workspace_id, herdr_tab_id: $herdr_tab_id,
      herdr_pane_id: $herdr_pane_id, agent_name: $agent_name,
      agent_kind: $agent_kind, agent_status: $agent_status, model: $model,
      reasoning_effort: $reasoning_effort, prompt_mode: $prompt_mode,
      prompt_submission: $prompt_submission,
      worktree_resumed: $worktree_resumed, workspace_resumed: $workspace_resumed,
      agent_resumed: $agent_resumed, prompt_resumed: $prompt_resumed}' >"$state_tmp"
  mv "$state_tmp" "$state_path"
}

recorded_checkpoint=''
if [[ -f "$state_path" ]]; then
  jq -e \
    --arg issue "$issue" --arg branch "$branch" --arg handoff "$handoff" \
    --arg handoff_hash "$handoff_hash" --arg parent_repo "$parent_repo" \
    --arg base_revision "$base_revision" --arg organization "$organization" \
    --arg project "$project" --arg repository_name "$repository_name" \
    --arg repository_remote "$repository_remote" --arg agent_mode "$agent_mode" \
    --arg prompt_mode "$prompt_mode" \
    '.issue == $issue and .branch == $branch and .handoff == $handoff
     and .handoff_hash == $handoff_hash and .parent_repo == $parent_repo
     and .base_revision == $base_revision and .organization == $organization
     and .project == $project and .repository_name == $repository_name
     and .repository_remote == $repository_remote and .agent_mode == $agent_mode
     and .prompt_mode == $prompt_mode' "$state_path" >/dev/null \
    || fail 'state does not exactly match the handoff and repository'
  recorded_checkpoint="$(jq -er '.checkpoint' "$state_path")" \
    || fail 'state has no checkpoint'
  recorded_rank="$(checkpoint_rank "$recorded_checkpoint")" \
    || fail 'state has an unknown checkpoint'
  if [[ "$(jq -r '.prompt_submission // "not-started"' "$state_path")" == pending ]]; then
    checkpoint="$recorded_checkpoint"
    fail 'prompt submission is pending; refusing an ambiguous resend'
  fi
fi
if (( recorded_rank == 0 )); then write_state; fi

worktree_path="$(git -C "$parent_repo" worktree list --porcelain | awk -v branch="refs/heads/$branch" '
  /^worktree / { path = substr($0, 10) }
  /^branch / && substr($0, 8) == branch { print path; found = 1; exit }
  END { if (found) exit 0; exit 1 }')" || true

if git -C "$parent_repo" show-ref --verify --quiet "refs/heads/$branch"; then
  [[ -n "$worktree_path" ]] || fail "branch exists without its expected worktree: $branch"
  [[ "$(git -C "$worktree_path" rev-parse HEAD)" == "$base_revision" ]] \
    || fail "worktree HEAD does not match base revision: $worktree_path"
  [[ -z "$(git -C "$worktree_path" status --porcelain)" ]] \
    || fail "worktree is not clean: $worktree_path"
  worktree_resumed=true
else
  (( recorded_rank < 2 )) || fail 'recorded Worktrunk checkout is missing'
  [[ -z "$worktree_path" ]] || fail "worktree exists without its expected branch: $worktree_path"
  (cd "$parent_repo" && wt switch --create --base "$base_revision" --no-cd "$branch") >/dev/null \
    || fail "Worktrunk could not create branch: $branch"
  worktree_path="$(git -C "$parent_repo" worktree list --porcelain | awk -v branch="refs/heads/$branch" '
    /^worktree / { path = substr($0, 10) }
    /^branch / && substr($0, 8) == branch { print path; found = 1; exit }
    END { if (found) exit 0; exit 1 }')" || fail 'created branch has no resolvable checkout'
fi
checkpoint=worktree-created
if (( recorded_rank >= 2 )); then
  jq -e --arg path "$worktree_path" '.worktree_path == $path' "$state_path" >/dev/null \
    || fail 'recorded Worktrunk checkout path does not match'
fi
if (( recorded_rank < 2 )); then write_state; fi

label="#${issue} ${slug//-/ }"
workspace_list="$(herdr workspace list)" || fail 'Herdr workspace listing failed'
workspace_count="$(jq -er --arg path "$worktree_path" \
  '[.result.workspaces[] | select(.worktree.checkout_path == $path)] | length' <<<"$workspace_list")" \
  || fail 'Herdr workspace listing has an unexpected schema'

if [[ "$workspace_count" == 1 ]]; then
  workspace_match="$(jq -cer --arg path "$worktree_path" --arg repo "$parent_repo" --arg label "$label" \
    '.result.workspaces[]
     | select(.worktree.checkout_path == $path)
     | select(.worktree.is_linked_worktree == true)
     | select(.worktree.repo_root == $repo)
     | select(.label == $label)
     | select(.tab_count == 1 and .pane_count == 1)' <<<"$workspace_list")" \
    || fail "Herdr workspace does not exactly match the partial launch: $worktree_path"
  herdr_workspace_id="$(jq -er '.workspace_id' <<<"$workspace_match")"
  herdr_tab_id="$(jq -er '.active_tab_id' <<<"$workspace_match")"
  pane_list="$(herdr pane list --workspace "$herdr_workspace_id")" \
    || fail "Herdr pane listing failed: $herdr_workspace_id"
  herdr_pane_id="$(jq -er --arg workspace "$herdr_workspace_id" --arg tab "$herdr_tab_id" \
    '[.result.panes[] | select(.workspace_id == $workspace and .tab_id == $tab)]
     | if length == 1 then .[0].pane_id else empty end' <<<"$pane_list")" \
    || fail "Herdr workspace does not have exactly one root pane: $herdr_workspace_id"
  workspace_resumed=true
elif [[ "$workspace_count" == 0 ]]; then
  (( recorded_rank < 3 )) || fail 'recorded Herdr workspace is missing'
  # The calling Herdr workspace may belong to a different repository.
  herdr_json="$(herdr worktree open \
    --cwd "$parent_repo" \
    --path "$worktree_path" \
    --label "$label" \
    --no-focus)" || fail 'Herdr worktree open failed'
  herdr_workspace_id="$(jq -er '.result.workspace.workspace_id' <<<"$herdr_json")" \
    || fail 'Herdr response is missing the workspace ID'
  herdr_tab_id="$(jq -er '.result.tab.tab_id' <<<"$herdr_json")" \
    || fail 'Herdr response is missing the tab ID'
  herdr_pane_id="$(jq -er '.result.root_pane.pane_id' <<<"$herdr_json")" \
    || fail 'Herdr response is missing the root-pane ID'
  jq -e --arg path "$worktree_path" --arg repo "$parent_repo" \
    '.result.workspace.worktree.checkout_path == $path
     and .result.workspace.worktree.is_linked_worktree == true
     and .result.workspace.worktree.repo_root == $repo' <<<"$herdr_json" >/dev/null \
    || fail "Herdr linked-worktree response does not match: $worktree_path"
else
  fail "multiple Herdr workspaces claim the worktree: $worktree_path"
fi
checkpoint=workspace-open
if (( recorded_rank >= 3 )); then
  jq -e --arg workspace "$herdr_workspace_id" --arg tab "$herdr_tab_id" \
    --arg pane "$herdr_pane_id" \
    '.herdr_workspace_id == $workspace and .herdr_tab_id == $tab
     and .herdr_pane_id == $pane' "$state_path" >/dev/null \
    || fail 'recorded Herdr workspace IDs do not match'
fi
if (( recorded_rank < 3 )); then write_state; fi

agent_list="$(herdr agent list)" || fail 'Herdr agent listing failed'
pane_agent_count="$(jq -er --arg pane "$herdr_pane_id" \
  '[.result.agents[] | select(.pane_id == $pane)] | length' <<<"$agent_list")" \
  || fail 'Herdr agent listing has an unexpected schema'
named_agent_count="$(jq -er --arg name "$agent_name" \
  '[.result.agents[] | select(.name == $name)] | length' <<<"$agent_list")" \
  || fail 'Herdr agent listing has an unexpected schema'

if [[ "$pane_agent_count" == 0 && "$named_agent_count" == 0 ]]; then
  (( recorded_rank < 4 )) || fail 'recorded Herdr agent is missing'
  if herdr agent get "$herdr_pane_id" >/dev/null 2>&1; then
    fail "root pane contains an unrecorded live agent: $herdr_pane_id"
  fi
  if [[ "$agent_kind" == codex ]]; then
    expected_argv="$(jq -cn --arg model "$model" --arg effort "$reasoning_effort" \
      '["codex", "-m", $model, "-c", "model_reasoning_effort=" + $effort]')"
    agent_start_command=(herdr agent start "$agent_name" --kind codex --pane "$herdr_pane_id" -- \
      -m "$model" -c "model_reasoning_effort=$reasoning_effort")
  else
    expected_argv="$(jq -cn --arg model "$model" --arg effort "$reasoning_effort" \
      '["pi", "--model", $model + ":" + $effort]')"
    agent_start_command=(herdr agent start "$agent_name" --kind pi --pane "$herdr_pane_id" -- \
      --model "$model:$reasoning_effort")
  fi
  start_agent || fail "Herdr could not start the $agent_kind agent"
  jq -e --arg name "$agent_name" --arg kind "$agent_kind" --arg pane "$herdr_pane_id" \
    --arg workspace "$herdr_workspace_id" --argjson expected_argv "$expected_argv" \
    '.result.type == "agent_started" and .result.agent.name == $name
     and .result.agent.agent == $kind and .result.agent.pane_id == $pane
     and .result.agent.workspace_id == $workspace
     and .result.agent.interactive_ready == true
     and .result.argv == $expected_argv' <<<"$agent_json" >/dev/null \
    || fail 'Herdr agent-start response does not match the launch'
  agent_status="$(jq -er '.result.agent.agent_status' <<<"$agent_json")"
else
  [[ "$pane_agent_count" == 1 && "$named_agent_count" == 1 ]] \
    || fail 'Herdr agent name or pane collides with another launch'
  agent_match="$(jq -cer --arg name "$agent_name" --arg pane "$herdr_pane_id" \
    --arg workspace "$herdr_workspace_id" --arg kind "$agent_kind" \
    '.result.agents[] | select(.name == $name and .pane_id == $pane
      and .workspace_id == $workspace and .agent == $kind)' <<<"$agent_list")" \
    || fail 'Herdr agent does not exactly match the partial launch'
  [[ -n "$recorded_checkpoint" ]] \
    || fail 'Herdr agent exists without matching launch state'
  jq -e --arg name "$agent_name" --arg kind "$agent_kind" --arg pane "$herdr_pane_id" --arg model "$model" \
    --arg effort "$reasoning_effort" \
    '.agent_name == $name and .agent_kind == $kind and .herdr_pane_id == $pane and .model == $model
     and .reasoning_effort == $effort' "$state_path" >/dev/null \
    || fail 'recorded agent state does not match the live agent'
  agent_status="$(jq -er '.agent_status' <<<"$agent_match")"
  agent_resumed=true
fi
checkpoint=agent-ready
if (( recorded_rank < 4 )); then write_state; fi

if [[ "$recorded_checkpoint" == prompted ]]; then
  prompt_submission=accepted
  prompt_resumed=true
else
  if [[ "$prompt_mode" == implement ]]; then
    # $tengella-deliver owns readiness, verification, PR, review, CI, and the
    # Review transition; this prompt adds only what the launch knows: the claim
    # already happened, and the human is not watching this pane.
    mode_instruction="Run \$tengella-deliver for issue #$issue. The launch already claimed it, so its state should read back as the implementation state. Review is the stopping point; landing belongs to \$tengella-finish under human direction. When you stop, at Review or on a blocker, announce it once with: herdr notification show \"#$issue: Review\" --body \"<PR link>\" --sound done, or herdr notification show \"#$issue: blocked\" --body \"<blocker>\" --sound request. Then end your turn with the outcome, PR, CI status, and remaining human gates."
  else
    mode_instruction='Perform setup only, summarize your understanding, and wait for direction.'
  fi
  setup_prompt="Read the immutable issue handoff at $handoff. Read every applicable AGENTS.md before acting. Treat the handoff as the authoritative implementation scope; use fresh tracker reads only for lifecycle updates and explicitly requested related evidence. $mode_instruction"
  [[ -z "$start_prompt" ]] || setup_prompt+=" Additional direction: $start_prompt"
  prompt_submission=pending
  write_state
  prompt_json="$(herdr agent prompt "$agent_name" "$setup_prompt")" \
    || fail 'Herdr did not accept the setup prompt'
  jq -e --arg name "$agent_name" --arg pane "$herdr_pane_id" --arg workspace "$herdr_workspace_id" \
    '.result.type == "agent_prompted" and .result.agent.name == $name
     and .result.agent.pane_id == $pane and .result.agent.workspace_id == $workspace' \
    <<<"$prompt_json" >/dev/null || fail 'Herdr prompt response does not match the launch'
  agent_status="$(jq -er '.result.agent.agent_status' <<<"$prompt_json")"
  prompt_submission=accepted
fi
checkpoint=prompted
write_state
cat "$state_path"
