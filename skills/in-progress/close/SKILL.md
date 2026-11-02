---
name: close
description: Close an issue after its PRs merge and answer its origin.
disable-model-invocation: true
---

# Close

Close one issue whose PRs have merged, so that the issue, its origin and the local machine all agree
that the work is finished.

## 1. Confirm the merge

Check that every PR linked from the issue has merged. If any is open or was closed unmerged, stop
and report which.

## 2. Set the issue straight

- Status: done.
- Tags/labels: match what was actually shipped (area, type, repos touched).
- Closing note: record only what a future reader would need and could not get from the PRs, such as
  a follow-up, a known limitation, or a gotcha found on the way. Skip the note when there is nothing
  like that.

## 3. Answer the origin

If the issue has an origin Ticket or Order, draft its answer: what was changed, in the origin's
terms, and what the requester needs to do, if anything. Show the draft and post it only after the
human approves, since it reaches people outside the team.

## 4. Clean up

Remove the worktrees and the merged local and remote branches this issue created.

Done when the issue is closed with correct status and tags, the origin has its answer, and no
worktree or branch from this issue remains.
