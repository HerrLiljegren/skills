---
name: pr-walkthrough
description: Open a Herdr tab where a Codex reviewer walks me through a PR or branch in Hunk.
disable-model-invocation: true
---

# PR walkthrough

Launch an interactive review: a new Herdr tab with a Codex reviewer on the left
and a Hunk diff on the right. The reviewer annotates the diff and then talks
the change through with the user. Its playbook is [`REVIEWER.md`](REVIEWER.md);
this skill only launches it.

## Workflow

1. Resolve the target from the arguments: an Azure DevOps PR number, a branch
   name, or a worktree path. With no argument, ask for one.

2. For a PR number, read its owning repository before selecting a checkout:

   ```bash
   AZURE_LOGGING_ENABLE_LOG_FILE=false az repos pr show --id <number> \
     --query '{repository:repository.name,sshUrl:repository.sshUrl,remoteUrl:repository.remoteUrl,source:sourceRefName,target:targetRefName}' -o json
   ```

   Locate the existing local checkout using applicable repository-routing
   guidance. Verify its `git remote get-url origin` matches the PR repository's
   SSH or HTTPS URL. If no matching checkout is known, ask for its path.
   A shared branch name or the caller's working directory does not establish
   repository identity. The launcher rejects a mismatch before fetching or
   creating a worktree.

   Keep the Herdr destination separate from the code checkout: use the calling
   pane's live workspace or the user's explicitly selected workspace. If the
   inherited pane is stale, resolve the destination with the user first.

3. From inside the verified repository, run:

   ```bash
   "$HOME/.agents/skills/pr-walkthrough/scripts/launch.sh" <target>
   ```

   The script defaults to `gpt-6.1-sol` at low effort. Pass `--model` or
   `--effort` only when the user asks for them.

   If the script fails, report its error verbatim and ask the user how to
   proceed. Switching model, harness, or launch method is the user's call.

   Done when the script exits `0` and prints the tab, reviewer, worktree, and
   diff.

4. Report the tab, reviewer name, worktree, and diff range. Tell the user to
   talk to the reviewer in the left pane; notes they leave in Hunk are picked
   up on their next message.
