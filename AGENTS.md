# Repository guidance

## Purpose

This repository contains personal, reusable agent skills. Skill contents are
the source of truth; harness skill directories are installation surfaces only.

## Skill layout

Organize skills into bucket folders under `skills/`:

- `engineering/` — daily code and technical work
- `productivity/` — daily non-code workflows and personal utilities
- `misc/` — useful but rarely used skills that are not promoted
- `in-progress/` — unfinished or experimental skills, not active by default
- `deprecated/` — retired skills kept only when their history remains useful

Create a bucket only when it contains a skill. Do not add empty scaffolding.

`engineering/` and `productivity/` are promoted buckets. Promoted skills belong
in the top-level README inventory and may be added to the portable catalog.
Skills in `misc/`, `in-progress/`, and `deprecated/` stay out of default
installation and catalog manifests.

Each bucket has a `README.md` whose skill names link to their `SKILL.md` files.
Promoted bucket READMEs and the top-level README group skills into
**User-invoked** and **Model-invoked**. Non-promoted buckets use a flat list.

## Authoring skills

- Put each skill at `skills/<bucket>/<skill-name>/SKILL.md`.
- Keep `name` and `description` frontmatter accurate and concise.
- Keep supporting scripts, references, templates, and assets beside the skill.
- Use paths relative to the skill or stable locations such as
  `$HOME/.agents/skills/<skill-name>`; do not embed checkout paths.
- Keep credentials, authentication state, account identifiers, and private
  output out of the repository.
- Moving a skill between buckets is its promotion or retirement decision;
  update its README/catalog entry in the same change when applicable.
- Classify every skill as user-invoked or model-invoked and keep harness
  metadata consistent; see [`.agents/invocation.md`](./.agents/invocation.md).

The top-level README lists promoted skills only and links each name directly to
its `SKILL.md`.

## Verification

- Run the available skill validator for every changed `SKILL.md`.
- Run `bash -n` for changed shell scripts.
- Search changed skills for stale checkout paths before committing.
- Do not activate, deactivate, publish, or install skills unless the task
  explicitly includes that external change.
