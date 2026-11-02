---
name: where-were-we
description:
  Recover work context when resuming a thread, inspecting a branch or workspace, or summarizing
  activity across projects for a standup or time window. Produce a concise, evidence-backed
  past/present/next brief.
model: sonnet
---

# Where Were We

Recover enough context to explain the last intent, current state, and next decision. Stay read-only
unless the user also asks to continue work.

## Workflow

1. Anchor the request.
   - Infer the subject, purpose, and time window from the request and current conversation: resume
     one task, inspect a workspace, or summarize activity across projects. Resolve relative dates
     using the user's timezone.
   - Prefer explicitly named threads, repositories, issues, and dates. Use the current directory
     only as a fallback; a scratch directory may be incidental.
   - Ask only when competing anchors would materially change the answer and available context cannot
     resolve them.
   - Done: scope and intended output are clear, with material assumptions stated.

2. Recover intent and actions.
   - Start with the current conversation and referenced handoffs or threads. In T3, use available
     thread search/read tools for the scoped subject and dates. Otherwise use the relevant terminal
     context below.
   - In Herdr, run the `herdr` skill to identify the current workspace and pane before reading
     recent history. Read sibling panes only when tied to the subject. Inspect tmux only when
     available and relevant.
   - If those sources are insufficient, search provider session records by project, thread, or date;
     read only the relevant turn window. Keep raw session history and authentication state private;
     report task-relevant findings only.
   - Expand a search only to resolve a named gap. A non-Git workspace can still have sufficient
     conversation evidence.
   - Done: recover the latest relevant intent, actions, and unresolved decisions, or identify
     exactly which evidence is unavailable.

3. Inspect the scoped repositories when current Git state matters.
   - Identify root, branch, and worktree relationship with `git rev-parse --show-toplevel`,
     `git branch --show-current`, and `git rev-parse --git-common-dir`. Use
     `git status --short --branch` once for dirty state, untracked paths, and available upstream
     synchronization information.
   - Inspect both unstaged and staged changes: `git diff --stat`, `git diff --cached --stat`; use
     their `--name-status` variants or focused diffs when needed to explain the work.
   - Separate tracking-upstream synchronization from task scope. Discover the task base from the PR
     target, repository conventions, or Worktrunk metadata even when an upstream exists. Inspect
     `git log --oneline <base>..HEAD` and `git diff --stat <base>...HEAD` for task work. State when
     the base is unknown.
   - Treat local remote-tracking refs as the last known remote state. Use read-only hosting tools
     when current PR or CI status matters.
   - For activity summaries, bound history by the requested dates and projects; deduplicate
     commits/work items across branches and threads. Distinguish the user's work from other
     contributors' activity.
   - Done: explain relevant changes and synchronization separately, including staged/untracked work
     and any unknown base. Skip Git when it adds no evidence needed for the requested brief.

4. Resolve work-item and verification context.
   - Follow issue IDs and handoff paths tied to the scoped task. Read repository sources first; use
     configured tracker tools when current title/status or requirements matter. Recent unrelated
     commits are not evidence of task scope.
   - For consequential claims distinguish **observed now**, **reported earlier**, and
     **unresolved**; label inference explicitly. Link concise evidence where useful rather than
     reproducing command output.
   - A historical test result applies to its recorded revision and environment. Check whether
     relevant code/configuration changed before describing it as current verification; if that
     cannot be established, retain the historical label. Distinguish local checks, CI, deployment,
     and human acceptance.
   - Name the cheapest check that would resolve a material uncertainty. Run validation only when
     requested; reuse applicable passing evidence.
   - Done: each material status claim has a source and freshness boundary, and remaining uncertainty
     has a concrete next check.

5. Write the brief.
   - Lead with what is done, what remains, or the decision the user needs to make.
   - Use the shape below for resuming work. Honor requested language and format; standups usually
     need a few outcome bullets, not a workspace inventory.
   - Omit empty or irrelevant fields. Include a stop/ask point only for an actual decision or
     authorization boundary; retain authorization already given.
   - Stop collecting evidence once intent, relevant state, and next decision are supported. State
     missing coverage rather than implying an exhaustive survey.
   - Done: the user can resume or report the work without reconstructing the investigation.

## Default brief

**Where We Were**

- Last intent and relevant issue:
- Recent actions:

**Where We Are**

- Current outcome and remaining work:
- Repo/branch/workspace when relevant:
- Verification and material uncertainty:

**Where We Are Going**

- Next best step:
- Decision or stop point, if any:
