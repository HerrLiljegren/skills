import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(import.meta.dirname, "..");
const script = path.join(root, "scripts", "launch-worktree.sh");
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "launch-issue-"));
process.once("exit", () => fs.rmSync(temporary, { recursive: true, force: true }));
const repository = path.join(temporary, "repository");
const bin = path.join(temporary, "bin");
const handoff = path.join(temporary, "launch-handoff.json");
const state = path.join(temporary, "launch-state.json");
const herdrState = path.join(temporary, "herdr-state");
const herdrAgentState = path.join(temporary, "agent-state");
const herdrManualAgentState = path.join(temporary, "manual-agent-state");
const wtLog = path.join(temporary, "wt.log");
const herdrOpenLog = path.join(temporary, "herdr-open.log");
const herdrAgentAttemptLog = path.join(temporary, "herdr-agent-attempt.log");
const herdrAgentStartLog = path.join(temporary, "herdr-agent-start.log");
const herdrPromptLog = path.join(temporary, "herdr-prompt.log");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { encoding: "utf8", ...options });
  if (result.status !== 0) {
    throw new Error(`${command} failed (${result.status})\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}`);
  }
  return result.stdout;
}

function executable(name, body) {
  const target = path.join(bin, name);
  fs.writeFileSync(target, `#!/usr/bin/env bash\nset -euo pipefail\n${body}`);
  fs.chmodSync(target, 0o755);
}

fs.mkdirSync(repository, { recursive: true });
fs.mkdirSync(bin);
run("git", ["init", "-q", repository]);
run("git", ["-C", repository, "config", "user.name", "Launch Issue Test"]);
run("git", ["-C", repository, "config", "user.email", "launch-issue-test@example.invalid"]);
const repositoryRemote = "git@ssh.dev.azure.com:v3/tengella/kundportalen/web-app";
run("git", ["-C", repository, "remote", "add", "origin", repositoryRemote]);
fs.writeFileSync(path.join(repository, "README.md"), "fixture\n");
run("git", ["-C", repository, "add", "README.md"]);
run("git", ["-C", repository, "commit", "-qm", "test: initialize fixture"]);
const baseRevision = run("git", ["-C", repository, "rev-parse", "HEAD"]).trim();
const handoffDocument = {
  id: 5423,
  url: "https://dev.azure.com/tengella/kundportalen/_workitems/edit/5423",
  type: "Bug",
  title: "Isolate cookies",
  state: "Active",
  assignee: { id: "user-1", displayName: "Launch Issue Test" },
  agentMode: "HITL",
  description: "Check access-token refresh and cookie flags without storing their values.",
  acceptanceCriteria: "- Refresh succeeds.",
  implementationNotes: "",
  verificationNotes: "",
  relations: [],
  worker: { kind: "codex", model: "gpt-6.1-sol", reasoning: "medium" },
  repository: {
    organization: "tengella",
    project: "kundportalen",
    name: "web-app",
    remote: repositoryRemote,
    root: repository,
    baseBranch: "main",
    baseCommit: baseRevision,
  },
};
fs.writeFileSync(handoff, `${JSON.stringify(handoffDocument)}\n`);

executable("wt", String.raw`
[[ "$1" == switch && "$2" == --create && "$3" == --base && "$5" == --no-cd ]]
base="$4"
branch="$6"
checkout="$LAUNCH_TEST_CHECKOUT"
printf '%s\n' "$branch" >>"$LAUNCH_TEST_WT_LOG"
git worktree add -q -b "$branch" "$checkout" "$base"
`);
executable("herdr", String.raw`
if [[ "$1 $2" == "worktree open" ]]; then
  has_workspace=0
  has_cwd=0
  for argument in "$@"; do
    [[ "$argument" == --workspace ]] && has_workspace=1
    [[ "$argument" == --cwd ]] && has_cwd=1
  done
  if (( has_workspace && has_cwd )); then
    echo 'herdr contract violation: --workspace and --cwd are mutually exclusive' >&2
    exit 2
  fi
  # The caller workspace belongs to another repository. Resolve by verified cwd.
  if (( has_workspace || ! has_cwd )); then
    echo 'worktree_not_found: caller workspace belongs to another repository' >&2
    exit 1
  fi
  [[ "$3" == --cwd && "$4" == "$LAUNCH_TEST_REPOSITORY" ]]
  [[ "$5" == --path && "$6" == "$LAUNCH_TEST_CHECKOUT" ]]
  printf 'open\n' >>"$LAUNCH_TEST_HERDR_OPEN_LOG"
  touch "$LAUNCH_TEST_HERDR_STATE"
  jq -n --arg path "$LAUNCH_TEST_CHECKOUT" --arg repo "$LAUNCH_TEST_REPOSITORY" \
    '{id:"cli:worktree:open",result:{already_open:false,root_pane:{pane_id:"w2:p1",tab_id:"w2:t1",workspace_id:"w2"},tab:{tab_id:"w2:t1",workspace_id:"w2"},type:"worktree_opened",workspace:{active_tab_id:"w2:t1",workspace_id:"w2",worktree:{checkout_path:$path,is_linked_worktree:true,repo_root:$repo}}}}'
  exit
fi
if [[ "$1 $2" == "workspace list" ]]; then
  if [[ ! -f "$LAUNCH_TEST_HERDR_STATE" ]]; then
    printf '{"id":"cli:workspace:list","result":{"type":"workspace_list","workspaces":[]}}\n'
    exit
  fi
  label="$LAUNCH_TEST_LABEL"
  [[ "$(cat "$LAUNCH_TEST_HERDR_STATE")" == conflict ]] && label='wrong launch'
  workspace=w2
  [[ "$(cat "$LAUNCH_TEST_HERDR_STATE")" == replaced ]] && workspace=w9
  jq -n --arg path "$LAUNCH_TEST_CHECKOUT" --arg repo "$LAUNCH_TEST_REPOSITORY" --arg label "$label" --arg workspace "$workspace" \
    '{id:"cli:workspace:list",result:{type:"workspace_list",workspaces:[{workspace_id:$workspace,active_tab_id:($workspace+":t1"),label:$label,tab_count:1,pane_count:1,worktree:{checkout_path:$path,is_linked_worktree:true,repo_root:$repo}}]}}'
  exit
fi
if [[ "$1 $2" == "pane list" ]]; then
  workspace="$4"
  jq -n --arg workspace "$workspace" \
    '{id:"cli:pane:list",result:{type:"pane_list",panes:[{pane_id:($workspace+":p1"),tab_id:($workspace+":t1"),workspace_id:$workspace}]}}'
  exit
fi
if [[ "$1 $2" == "agent list" ]]; then
  if [[ ! -f "$LAUNCH_TEST_AGENT_STATE" ]]; then
    printf '{"id":"cli:agent:list","result":{"type":"agent_list","agents":[]}}\n'
    exit
  fi
  jq -n --arg name "$LAUNCH_TEST_AGENT_NAME" --arg kind "$LAUNCH_TEST_AGENT_KIND" \
    '{id:"cli:agent:list",result:{type:"agent_list",agents:[{name:$name,agent:$kind,agent_status:"idle",pane_id:"w2:p1",tab_id:"w2:t1",workspace_id:"w2"}]}}'
  exit
fi
if [[ "$1 $2" == "agent get" ]]; then
  if [[ -f "$LAUNCH_TEST_MANUAL_AGENT_STATE" ]]; then
    jq -n --arg kind "$LAUNCH_TEST_AGENT_KIND" \
      '{id:"cli:agent:get",result:{type:"agent_info",agent:{agent:$kind,agent_status:"idle",pane_id:"w2:p1",tab_id:"w2:t1",workspace_id:"w2"}}}'
    exit
  fi
  jq -n '{error:{code:"agent_not_found",message:"no agent in pane"},id:"cli:agent:get"}' >&2
  exit 1
fi
if [[ "$1 $2" == "agent start" ]]; then
  [[ "$*" == "$LAUNCH_TEST_EXPECTED_START" ]] || {
    echo "unexpected agent start: $*" >&2
    exit 2
  }
  printf '%s\n' "$*" >>"$LAUNCH_TEST_AGENT_ATTEMPT_LOG"
  attempt="$(wc -l <"$LAUNCH_TEST_AGENT_ATTEMPT_LOG")"
  if (( attempt <= LAUNCH_TEST_BUSY_ATTEMPTS )); then
    jq -n '{error:{code:"agent_pane_busy",message:"agent target pane w2:p1 is not an available shell"},id:"cli:agent:start"}' >&2
    exit 1
  fi
  printf '%s\n' "$*" >>"$LAUNCH_TEST_AGENT_START_LOG"
  touch "$LAUNCH_TEST_AGENT_STATE"
  jq -n --arg name "$LAUNCH_TEST_AGENT_NAME" --arg kind "$LAUNCH_TEST_AGENT_KIND" \
    --argjson argv "$LAUNCH_TEST_AGENT_ARGV" \
    '{id:"cli:agent:start",result:{type:"agent_started",argv:$argv,agent:{name:$name,agent:$kind,agent_status:"idle",interactive_ready:true,pane_id:"w2:p1",tab_id:"w2:t1",workspace_id:"w2"}}}'
  exit
fi
if [[ "$1 $2" == "agent prompt" ]]; then
  for argument in "$@"; do
    [[ "$argument" != --wait ]] || { echo 'daily launch must not wait for worker completion' >&2; exit 2; }
  done
  printf '%s\n' "$*" >>"$LAUNCH_TEST_PROMPT_LOG"
  jq -n --arg name "$LAUNCH_TEST_AGENT_NAME" --arg kind "$LAUNCH_TEST_AGENT_KIND" \
    '{id:"cli:agent:prompt",result:{type:"agent_prompted",agent:{name:$name,agent:$kind,agent_status:"working",pane_id:"w2:p1",tab_id:"w2:t1",workspace_id:"w2"}}}'
  exit
fi
echo "unexpected herdr invocation: $*" >&2
exit 64
`);
executable("codex", "exit 0\n");
executable("pi", "exit 0\n");

const environment = {
  ...process.env,
  PATH: `${bin}:${process.env.PATH}`,
  HERDR_ENV: "1",
  HERDR_WORKSPACE_ID: "other-repository-workspace",
  LAUNCH_TEST_REPOSITORY: repository,
  LAUNCH_TEST_CHECKOUT: path.join(repository, ".worktrees", "issue-5423-isolate-cookies"),
  LAUNCH_TEST_HERDR_STATE: herdrState,
  LAUNCH_TEST_WT_LOG: wtLog,
  LAUNCH_TEST_HERDR_OPEN_LOG: herdrOpenLog,
  LAUNCH_TEST_AGENT_ATTEMPT_LOG: herdrAgentAttemptLog,
  LAUNCH_TEST_AGENT_STATE: herdrAgentState,
  LAUNCH_TEST_MANUAL_AGENT_STATE: herdrManualAgentState,
  LAUNCH_TEST_AGENT_START_LOG: herdrAgentStartLog,
  LAUNCH_TEST_PROMPT_LOG: herdrPromptLog,
  LAUNCH_TEST_LABEL: "#5423 isolate cookies",
  LAUNCH_TEST_AGENT_NAME: "issue5423",
  LAUNCH_TEST_AGENT_KIND: "codex",
  LAUNCH_TEST_EXPECTED_START: "agent start issue5423 --kind codex --pane w2:p1 -- -m gpt-6.1-sol -c model_reasoning_effort=medium",
  LAUNCH_TEST_AGENT_ARGV: JSON.stringify(["codex", "-m", "gpt-6.1-sol", "-c", "model_reasoning_effort=medium"]),
  LAUNCH_TEST_BUSY_ATTEMPTS: "2",
};

function launch(startPrompt) {
  const args = [handoff];
  if (startPrompt) args.push(startPrompt);
  return spawnSync(script, args, {
    cwd: repository,
    encoding: "utf8",
    env: environment,
  });
}

const invalidModeHandoff = path.join(temporary, "invalid-mode-handoff.json");
const invalidMode = JSON.parse(fs.readFileSync(handoff, "utf8"));
invalidMode.agentMode = "Other";
fs.writeFileSync(invalidModeHandoff, `${JSON.stringify(invalidMode)}\n`);
const invalidModeResult = spawnSync(script, [invalidModeHandoff], {
  cwd: repository,
  encoding: "utf8",
  env: environment,
});
assert.equal(invalidModeResult.status, 1);
assert.match(invalidModeResult.stderr, /agent mode must be AFK, HITL, or Human/);

const mismatchedProjectHandoff = path.join(temporary, "mismatched-project-handoff.json");
const mismatchedProject = JSON.parse(fs.readFileSync(handoff, "utf8"));
mismatchedProject.repository.project = "Tengella";
fs.writeFileSync(mismatchedProjectHandoff, `${JSON.stringify(mismatchedProject)}\n`);
const mismatchedProjectResult = spawnSync(script, [mismatchedProjectHandoff], {
  cwd: repository,
  encoding: "utf8",
  env: environment,
});
assert.equal(mismatchedProjectResult.status, 1);
assert.match(mismatchedProjectResult.stderr, /project and repository do not match/);

const result = launch("prefer the smallest seam");

assert.equal(
  result.status,
  0,
  `fresh launch must obey the Herdr selector contract\n${result.stderr}`,
);

const output = JSON.parse(result.stdout);
assert.equal(output.herdr_workspace_id, "w2");
assert.equal(output.herdr_tab_id, "w2:t1");
assert.equal(output.herdr_pane_id, "w2:p1");
assert.equal(output.agent_kind, "codex");
assert.equal(output.organization, "tengella");
assert.equal(output.project, "kundportalen");
assert.equal(output.repository_name, "web-app");
assert.equal(output.repository_remote, repositoryRemote);
assert.equal(output.agent_mode, "HITL");
assert.equal(output.checkpoint, "prompted");
assert.equal(output.base_revision, output.root_head);
assert.equal(output.worktree_resumed, false);
assert.equal(output.workspace_resumed, false);
assert.equal(fs.readFileSync(wtLog, "utf8"), "issue/5423-isolate-cookies\n");
assert.equal(fs.readFileSync(herdrAgentStartLog, "utf8").split("\n").filter(Boolean).length, 1);
assert.equal(fs.readFileSync(herdrAgentAttemptLog, "utf8").split("\n").filter(Boolean).length, 3);
assert.equal(fs.readFileSync(herdrPromptLog, "utf8").split("\n").filter(Boolean).length, 1);
assert.match(fs.readFileSync(herdrPromptLog, "utf8"), /Perform setup only/);
assert.match(fs.readFileSync(herdrPromptLog, "utf8"), /Additional direction: prefer the smallest seam/);
assert.equal(JSON.parse(fs.readFileSync(state, "utf8")).checkpoint, "prompted");
const promptedState = fs.readFileSync(state, "utf8");

const workspaceOpenState = JSON.parse(promptedState);
workspaceOpenState.checkpoint = "workspace-open";
workspaceOpenState.agent_status = "";
workspaceOpenState.prompt_submission = "not-started";
fs.writeFileSync(state, `${JSON.stringify(workspaceOpenState)}\n`);
fs.rmSync(herdrAgentState);
fs.writeFileSync(herdrManualAgentState, "manual\n");
const manualAgentAttempts = fs.readFileSync(herdrAgentAttemptLog, "utf8");
const manualAgentResume = launch();
assert.equal(manualAgentResume.status, 1);
const manualAgentFailure = JSON.parse(manualAgentResume.stdout);
assert.match(manualAgentFailure.error, /unrecorded live agent/);
assert.equal(manualAgentFailure.checkpoint, "workspace-open");
assert.equal(manualAgentFailure.herdr_workspace_id, "w2");
assert.equal(manualAgentFailure.herdr_tab_id, "w2:t1");
assert.equal(manualAgentFailure.herdr_pane_id, "w2:p1");
assert.equal(fs.readFileSync(herdrAgentAttemptLog, "utf8"), manualAgentAttempts);
fs.rmSync(herdrManualAgentState);
fs.writeFileSync(herdrAgentState, "named\n");
fs.writeFileSync(state, promptedState);

const mismatchedState = JSON.parse(promptedState);
mismatchedState.project = "Tengella";
fs.writeFileSync(state, `${JSON.stringify(mismatchedState)}\n`);
const mismatchedResume = launch();
assert.equal(mismatchedResume.status, 1);
assert.match(JSON.parse(mismatchedResume.stdout).error, /state does not exactly match/);
fs.writeFileSync(state, promptedState);

fs.writeFileSync(path.join(repository, "advanced.txt"), "advanced\n");
run("git", ["-C", repository, "add", "advanced.txt"]);
run("git", ["-C", repository, "commit", "-qm", "test: advance root after partial launch"]);
assert.notEqual(run("git", ["-C", repository, "rev-parse", "HEAD"]).trim(), output.root_head);
const resumedWorktree = launch();
assert.equal(
  resumedWorktree.status,
  0,
  `matching worktree must resume without another Worktrunk mutation\n${resumedWorktree.stderr}`,
);
assert.equal(fs.readFileSync(wtLog, "utf8"), "issue/5423-isolate-cookies\n");
assert.equal(fs.readFileSync(herdrOpenLog, "utf8"), "open\n");
const resumedWorktreeOutput = JSON.parse(resumedWorktree.stdout);
assert.equal(resumedWorktreeOutput.worktree_resumed, true);
assert.equal(resumedWorktreeOutput.workspace_resumed, true);
assert.equal(resumedWorktreeOutput.agent_resumed, true);
assert.equal(resumedWorktreeOutput.prompt_resumed, true);
assert.equal(resumedWorktreeOutput.herdr_pane_id, "w2:p1");
assert.equal(fs.readFileSync(wtLog, "utf8"), "issue/5423-isolate-cookies\n");
assert.equal(fs.readFileSync(herdrOpenLog, "utf8"), "open\n");
assert.equal(fs.readFileSync(herdrAgentStartLog, "utf8").split("\n").filter(Boolean).length, 1);
assert.equal(fs.readFileSync(herdrPromptLog, "utf8").split("\n").filter(Boolean).length, 1);

fs.writeFileSync(herdrState, "replaced\n");
const replacedRecordedWorkspace = launch();
assert.equal(replacedRecordedWorkspace.status, 1);
assert.match(JSON.parse(replacedRecordedWorkspace.stdout).error, /recorded Herdr workspace IDs do not match/);
assert.equal(fs.readFileSync(herdrOpenLog, "utf8"), "open\n");
fs.writeFileSync(herdrState, "matching\n");

fs.rmSync(herdrState);
const missingRecordedWorkspace = launch();
assert.equal(missingRecordedWorkspace.status, 1);
assert.match(JSON.parse(missingRecordedWorkspace.stdout).error, /recorded Herdr workspace is missing/);
assert.equal(fs.readFileSync(herdrOpenLog, "utf8"), "open\n");
fs.writeFileSync(herdrState, "matching\n");

fs.writeFileSync(herdrState, "conflict\n");
const conflictingWorkspace = launch();
assert.equal(conflictingWorkspace.status, 1);
assert.deepEqual(JSON.parse(conflictingWorkspace.stdout), {
  ok: false,
  issue: "5423",
  branch: "issue/5423-isolate-cookies",
  checkpoint: "worktree-created",
  handoff,
  state_path: state,
  parent_repo: repository,
  root_head: run("git", ["-C", repository, "rev-parse", "HEAD"]).trim(),
  base_revision: output.root_head,
  worktree_path: environment.LAUNCH_TEST_CHECKOUT,
  herdr_workspace_id: "",
  herdr_tab_id: "",
  herdr_pane_id: "",
  agent_name: "issue5423",
  agent_kind: "codex",
  model: "gpt-6.1-sol",
  reasoning_effort: "medium",
  prompt_submission: "not-started",
  error: `Herdr workspace does not exactly match the partial launch: ${environment.LAUNCH_TEST_CHECKOUT}`,
});
assert.equal(fs.readFileSync(herdrOpenLog, "utf8"), "open\n");
assert.equal(JSON.parse(fs.readFileSync(state, "utf8")).checkpoint, "prompted");

fs.writeFileSync(herdrState, "matching\n");
const pendingState = JSON.parse(promptedState);
pendingState.checkpoint = "agent-ready";
pendingState.prompt_submission = "pending";
fs.writeFileSync(state, `${JSON.stringify(pendingState)}\n`);
const ambiguousPrompt = launch();
assert.equal(ambiguousPrompt.status, 1);
assert.match(JSON.parse(ambiguousPrompt.stdout).error, /refusing an ambiguous resend/);
assert.equal(fs.readFileSync(herdrAgentStartLog, "utf8").split("\n").filter(Boolean).length, 1);
assert.equal(fs.readFileSync(herdrPromptLog, "utf8").split("\n").filter(Boolean).length, 1);
fs.writeFileSync(state, promptedState);

fs.writeFileSync(path.join(environment.LAUNCH_TEST_CHECKOUT, "changed.txt"), "changed\n");
run("git", ["-C", environment.LAUNCH_TEST_CHECKOUT, "add", "changed.txt"]);
run("git", ["-C", environment.LAUNCH_TEST_CHECKOUT, "commit", "-qm", "test: drift from base"]);
const conflictingWorktree = launch();
assert.equal(conflictingWorktree.status, 1);
assert.match(JSON.parse(conflictingWorktree.stdout).error, /worktree HEAD does not match base revision/);
assert.equal(fs.readFileSync(wtLog, "utf8"), "issue/5423-isolate-cookies\n");
assert.equal(fs.readFileSync(herdrOpenLog, "utf8"), "open\n");

const piRepository = path.join(temporary, "pi-repository");
const piHandoff = path.join(temporary, "pi-launch-handoff.json");
const piState = path.join(temporary, "pi-launch-state.json");
fs.mkdirSync(piRepository);
run("git", ["init", "-q", piRepository]);
run("git", ["-C", piRepository, "config", "user.name", "Launch Issue Test"]);
run("git", ["-C", piRepository, "config", "user.email", "launch-issue-test@example.invalid"]);
const piRepositoryRemote = "git@ssh.dev.azure.com:v3/tengella/Tengella/Tengella_bare";
run("git", ["-C", piRepository, "remote", "add", "origin", piRepositoryRemote]);
fs.writeFileSync(path.join(piRepository, "README.md"), "pi fixture\n");
run("git", ["-C", piRepository, "add", "README.md"]);
run("git", ["-C", piRepository, "commit", "-qm", "test: initialize pi fixture"]);
const piBaseRevision = run("git", ["-C", piRepository, "rev-parse", "HEAD"]).trim();
// Keep the requested base distinct from the invoking checkout and its dirty files.
run("git", ["-C", piRepository, "commit", "--allow-empty", "-qm", "test: advance pi root"]);
const piRootHead = run("git", ["-C", piRepository, "rev-parse", "HEAD"]).trim();
const piRootBranch = run("git", ["-C", piRepository, "branch", "--show-current"]).trim();
fs.writeFileSync(path.join(piRepository, "README.md"), "unrelated local changes\n");
fs.writeFileSync(piHandoff, `${JSON.stringify({
  id: 5426,
  type: "Issue",
  title: "Standardize CleanFlow authorization",
  state: "In Progress",
  agentMode: "AFK",
  worker: {
    kind: "pi",
    model: "opencode-go/gpt-5.6-luna",
    reasoning: "xhigh",
  },
  repository: {
    organization: "tengella",
    project: "Tengella",
    name: "Tengella_bare",
    remote: piRepositoryRemote,
    root: piRepository,
    baseBranch: "main",
    baseCommit: piBaseRevision,
  },
})}\n`);

const piEnvironment = {
  ...environment,
  LAUNCH_TEST_REPOSITORY: piRepository,
  LAUNCH_TEST_CHECKOUT: path.join(piRepository, ".worktrees", "issue-5426-standardize-cleanflow-authorization"),
  LAUNCH_TEST_HERDR_STATE: path.join(temporary, "pi-herdr-state"),
  LAUNCH_TEST_WT_LOG: path.join(temporary, "pi-wt.log"),
  LAUNCH_TEST_HERDR_OPEN_LOG: path.join(temporary, "pi-herdr-open.log"),
  LAUNCH_TEST_AGENT_STATE: path.join(temporary, "pi-agent-state"),
  LAUNCH_TEST_AGENT_START_LOG: path.join(temporary, "pi-agent-start.log"),
  LAUNCH_TEST_PROMPT_LOG: path.join(temporary, "pi-prompt.log"),
  LAUNCH_TEST_LABEL: "#5426 standardize cleanflow authorization",
  LAUNCH_TEST_AGENT_NAME: "issue5426",
  LAUNCH_TEST_AGENT_KIND: "pi",
  LAUNCH_TEST_EXPECTED_START: "agent start issue5426 --kind pi --pane w2:p1 -- --model opencode-go/gpt-5.6-luna:xhigh",
  LAUNCH_TEST_AGENT_ARGV: JSON.stringify(["pi", "--model", "opencode-go/gpt-5.6-luna:xhigh"]),
};
const piResult = spawnSync(script, [piHandoff], {
  cwd: piRepository,
  encoding: "utf8",
  env: piEnvironment,
});
assert.equal(piResult.status, 0, `Pi launch must succeed\n${piResult.stderr}`);
const piOutput = JSON.parse(piResult.stdout);
assert.equal(piOutput.checkpoint, "prompted");
assert.equal(piOutput.agent_kind, "pi");
assert.equal(piOutput.organization, "tengella");
assert.equal(piOutput.project, "Tengella");
assert.equal(piOutput.repository_name, "Tengella_bare");
assert.equal(piOutput.repository_remote, piRepositoryRemote);
assert.equal(piOutput.agent_mode, "AFK");
assert.equal(piOutput.model, "opencode-go/gpt-5.6-luna");
assert.equal(piOutput.reasoning_effort, "xhigh");
assert.equal(piOutput.base_revision, piBaseRevision);
assert.equal(piOutput.root_head, piRootHead);
assert.notEqual(piOutput.base_revision, piOutput.root_head);
assert.equal(run("git", ["-C", piEnvironment.LAUNCH_TEST_CHECKOUT, "rev-parse", "HEAD"]).trim(), piBaseRevision);
assert.equal(run("git", ["-C", piRepository, "rev-parse", "HEAD"]).trim(), piRootHead);
assert.equal(run("git", ["-C", piRepository, "branch", "--show-current"]).trim(), piRootBranch);
assert.equal(fs.readFileSync(path.join(piRepository, "README.md"), "utf8"), "unrelated local changes\n");
const afkPrompt = fs.readFileSync(piEnvironment.LAUNCH_TEST_PROMPT_LOG, "utf8");
assert.match(afkPrompt, /Run \$tengella-deliver for issue #/);
assert.match(afkPrompt, /Review is the stopping point/);
assert.match(afkPrompt, /herdr notification show "#\d+: Review"/);
assert.match(afkPrompt, /herdr notification show "#\d+: blocked"/);
assert.doesNotMatch(afkPrompt, /do not refetch the tracker/);
assert.doesNotMatch(fs.readFileSync(herdrPromptLog, "utf8"), /tengella-deliver/);
assert.equal(JSON.parse(fs.readFileSync(piState, "utf8")).checkpoint, "prompted");

console.log("launch-issue verification passed");
