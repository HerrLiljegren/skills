# Launcher verification

Run from the skill directory:

```sh
bash -n scripts/preflight.sh scripts/launch-worktree.sh
node --check tests/launch-issue.mjs
node tests/launch-issue.mjs
LAUNCH_TEST_LINKED=1 node tests/launch-issue.mjs
```

The test uses temporary Git repositories and stubbed Tengella, Worktrunk, Herdr and worker
executables. It performs no live launches or Boards mutations. Git, Bash, Node 24, jq and iconv are
required. The repository's `bash scripts/check.sh` entry point (from the repository root) includes
both test modes, and `.github/workflows/check.yml` runs it on pushes and PRs.

Coverage includes read-only local preflight with aggregated gaps, route mismatches, separate-issue
failure isolation, partial setup, conflicting live identities, ambiguous prompt submission, accepted
workers with commits and unfinished edits, immutable receipts on repeated launch, both worker
profiles, issue links and the delivery evidence/amendment prompt.

The orchestrator's semantic Ready evaluation, batch selection, live CLI capability discovery and
harness skill invocation remain separate acceptance checks. Script fixtures cannot prove those.
Before a live launch, use the installed shared workflow and CLI help to establish the required
capabilities; missing repository/current-identity/transition evidence blocks claiming.

For invocation acceptance, use `/launch-issue` in Claude and `$launch-issue` in Codex with the same
issue list and direction. Claude's `argument-hint` provides autocomplete guidance. The shared body
consumes invocation text and uses no argument-substitution placeholders. Generic Agent Skills
validators may flag the intentional Claude-specific `argument-hint` and `disable-model-invocation`
fields; `agents/openai.yaml` supplies Codex's matching explicit-invocation policy.
