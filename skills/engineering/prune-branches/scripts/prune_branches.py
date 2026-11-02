#!/usr/bin/env python3
"""Plan, then apply by digest, deletion of merged PR branches (local and remote).

A branch is prunable only when a PR from it merged into a target that still exists
on the remote (or into --base, when given) with the branch's current tip as its head
(or the tip is already in that target), no open PR uses the branch, and the PR did
not bypass branch policy. Every deletion is a
compare-and-delete on the planned SHA, so a branch that moved since planning is
left alone.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys


def run(*args, cwd=None, check=True):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"error: {' '.join(args)}\n{result.stderr.strip()}")
    return result


def git(repo, *args, check=True):
    return run("git", "-C", repo, *args, check=check)


def pull_requests(repo, remote_url):
    """Return dicts: src branch, tgt branch, state (open|merged|other), head SHA, bypass."""
    azure = re.search(
        r"(?:dev\.azure\.com[:/](?:v3/)?|@dev\.azure\.com/)([^/]+)/([^/]+)/(?:_git/)?([^/]+?)(?:\.git)?$",
        remote_url,
    )
    if azure:
        org, project, name = azure.groups()
        # The API returns at most 1000 PRs per call; page until a short page, or older
        # branches look PR-less and are silently skipped.
        raw, page = [], 1000
        while True:
            batch = json.loads(
                run(
                    "az", "repos", "pr", "list", "--org", f"https://dev.azure.com/{org}",
                    "-p", project, "-r", name, "--status", "all",
                    "--top", str(page), "--skip", str(len(raw)), "-o", "json",
                ).stdout
            )
            raw += batch
            if len(batch) < page:
                break
        states = {"active": "open", "completed": "merged"}
        return [
            {
                "id": pr["pullRequestId"],
                "src": pr["sourceRefName"].removeprefix("refs/heads/"),
                "tgt": pr["targetRefName"].removeprefix("refs/heads/"),
                "state": states.get(pr["status"], "other"),
                "head": (pr.get("lastMergeSourceCommit") or {}).get("commitId"),
                "bypass": bool((pr.get("completionOptions") or {}).get("bypassPolicy")),
            }
            for pr in raw
        ]
    if "github.com" in remote_url:
        raw = json.loads(
            run(
                "gh", "pr", "list", "--state", "all", "--limit", "100000",
                "--json", "number,state,headRefName,baseRefName,headRefOid",
                cwd=repo,
            ).stdout
        )
        states = {"OPEN": "open", "MERGED": "merged"}
        return [
            {
                "id": pr["number"],
                "src": pr["headRefName"],
                "tgt": pr["baseRefName"],
                "state": states.get(pr["state"], "other"),
                "head": pr["headRefOid"],
                "bypass": False,
            }
            for pr in raw
        ]
    sys.exit(f"error: unsupported PR host for remote {remote_url}")


def worktrees(repo):
    """Map branch -> worktree path, excluding the main worktree."""
    out, current, main = {}, {}, None
    for line in git(repo, "worktree", "list", "--porcelain").stdout.splitlines() + [""]:
        if line.startswith("worktree "):
            current = {"path": line[9:]}
            main = main or current["path"]
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch refs/heads/")
        elif not line and current.get("branch") and current["path"] != main:
            out[current["branch"]] = current["path"]
    return out, main


def occupants(path):
    """Process names whose cwd is inside path; None when /proc is unavailable."""
    if not os.path.isdir("/proc/self"):
        return None
    names = set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            cwd = os.readlink(f"/proc/{pid}/cwd")
            if cwd == path or cwd.startswith(path + os.sep):
                names.add(open(f"/proc/{pid}/comm").read().strip())
        except OSError:
            continue
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="any checkout of the repository")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--base", help="only count PRs merged into this branch (default: any target still on the remote)")
    parser.add_argument(
        "--protect", action="append", default=[], metavar="GLOB",
        help="branch glob never pruned, repeatable (always: main, master, develop, release/*)",
    )
    parser.add_argument("--apply", metavar="DIGEST", help="delete the plan whose printed digest is DIGEST")
    opts = parser.parse_args()

    repo = git(opts.repo, "rev-parse", "--show-toplevel").stdout.strip()
    git(repo, "fetch", "--quiet", "--prune", opts.remote)
    base = opts.base
    prs = pull_requests(repo, git(repo, "remote", "get-url", opts.remote).stdout.strip())
    trees, main_tree = worktrees(repo)
    main_branch = git(main_tree, "branch", "--show-current").stdout.strip()
    remote_branches = set(
        git(repo, "for-each-ref", "--format=%(refname:lstrip=3)", f"refs/remotes/{opts.remote}").stdout.split()
    )
    # Branches that merged PRs land in, and long-lived ones such as old releases that
    # were themselves merged onward, are never pruned.
    targets = {pr["tgt"] for pr in prs if pr["state"] == "merged"}
    protected = ["main", "master", "develop", "release/*", *opts.protect]

    def verdict(branch, sha):
        own = [pr for pr in prs if pr["src"] == branch]
        if not own:
            return None, "no PR"
        if any(pr["state"] == "open" for pr in own):
            return None, "open PR"
        merged = [
            pr for pr in own
            if pr["state"] == "merged" and not pr["bypass"] and (pr["tgt"] == base if base else True)
        ]
        # A target deleted from the remote no longer holds the work, so it does not count.
        live = [pr for pr in merged if pr["tgt"] in remote_branches]
        for pr in live:
            if pr["head"] == sha:
                return pr, f"PR {pr['id']} merged into {pr['tgt']} at tip"
        for pr in live:
            if git(repo, "merge-base", "--is-ancestor", sha, f"{opts.remote}/{pr['tgt']}", check=False).returncode == 0:
                return pr, f"PR {pr['id']} merged, tip in {opts.remote}/{pr['tgt']}"
        if live:
            return None, "tip has commits after the merged PR"
        if merged:
            return None, "merged PR target no longer on the remote"
        return None, f"PR not merged into {base}" if base else "PR not merged"

    plan_remote, plan_local, skipped = [], [], []
    refs = git(repo, "for-each-ref", "--format=%(refname) %(objectname)", f"refs/remotes/{opts.remote}", "refs/heads").stdout
    for line in refs.splitlines():
        ref, sha = line.split()
        remote = ref.startswith("refs/remotes/")
        branch = ref.removeprefix(f"refs/remotes/{opts.remote}/").removeprefix("refs/heads/")
        if branch in (base, "HEAD") or branch in targets:
            continue
        if any(fnmatch.fnmatchcase(branch, glob) for glob in protected):
            continue
        pr, reason = verdict(branch, sha)
        where = "remote" if remote else "local"
        if not remote and branch == main_branch:
            # Never switch the main checkout; report it so a merged branch there is not invisible.
            if pr:
                skipped.append((where, branch, f"{reason}; checked out in main worktree {main_tree}, switch it first"))
            continue
        if not pr:
            if reason != "no PR":
                skipped.append((where, branch, reason))
            continue
        if remote:
            plan_remote.append((branch, sha, reason))
            continue
        path = trees.get(branch)
        if path:
            if git(path, "status", "--porcelain").stdout.strip():
                skipped.append((where, branch, f"{reason}; worktree has uncommitted changes"))
                continue
            busy = occupants(path)
            if busy is None or busy:
                why = "occupancy unknown (no /proc)" if busy is None else "in use by " + ", ".join(sorted(busy))
                skipped.append((where, branch, f"{reason}; worktree {why}"))
                continue
        plan_local.append((branch, sha, reason, path))

    print(f"base {opts.remote}/{base}" if base else "base any merged PR target on " + opts.remote)
    for branch, sha, reason in plan_remote:
        print(f"delete remote  {branch}  {sha[:8]}  ({reason})")
    for branch, sha, reason, path in plan_local:
        print(f"delete local   {branch}  {sha[:8]}  ({reason})" + (f"  + worktree {path}" if path else ""))
    for where, branch, reason in skipped:
        print(f"keep {where:7}  {branch}  ({reason})")
    if not (plan_remote or plan_local):
        print("nothing to prune")
        return
    # The digest binds --apply to the exact plan the user approved.
    digest = hashlib.sha256(
        "\n".join(sorted([f"remote {b} {s}" for b, s, _ in plan_remote] + [f"local {b} {s}" for b, s, _, _ in plan_local])).encode()
    ).hexdigest()[:12]
    print(f"plan digest {digest}")
    if not opts.apply:
        return
    if opts.apply != digest:
        sys.exit(f"error: plan changed since approval (approved {opts.apply}, now {digest}); review the new plan")

    # Each deletion stands alone: one rejected lease or failed worktree removal is
    # reported and the rest of the approved plan still runs.
    failures = []
    if plan_remote:
        leases = [f"--force-with-lease=refs/heads/{b}:{s}" for b, s, _ in plan_remote]
        deletes = [f":refs/heads/{b}" for b, _, _ in plan_remote]
        # Azure Repos rejects --atomic; each lease still guards its own branch.
        pushed = git(repo, "push", "--porcelain", opts.remote, *leases, *deletes, check=False)
        # A rejected delete reads "!\t(delete):refs/heads/<branch>\t[rejected] ...".
        rejected = [
            line.split("\t")[1].rsplit(":", 1)[1].removeprefix("refs/heads/")
            for line in pushed.stdout.splitlines()
            if line.startswith("!\t")
        ]
        if pushed.returncode and not rejected:
            sys.exit(f"error: git push {opts.remote}\n{pushed.stderr.strip()}")
        failures += [f"remote {b}: rejected (moved since planning?)" for b in rejected]
        print(f"deleted {len(plan_remote) - len(rejected)} remote branches")
    deleted = 0
    for branch, sha, _, path in plan_local:
        if path:
            removed = run("wt", "-C", repo, "remove", "--foreground", "--no-delete-branch", branch, check=False)
            if removed.returncode:
                failures.append(f"local {branch}: worktree removal failed: {removed.stderr.strip()}")
                continue
        # update-ref with an old value deletes only if the branch still points at sha.
        updated = git(repo, "update-ref", "-d", f"refs/heads/{branch}", sha, check=False)
        if updated.returncode:
            failures.append(f"local {branch}: {updated.stderr.strip()}")
            continue
        deleted += 1
    if plan_local:
        print(f"deleted {deleted} local branches")
    for failure in failures:
        print(f"failed {failure}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
