# User-invoked and model-invoked skills

Every skill has one invocation mode:

- **User-invoked** skills run only when the human names them. Set
  `disable-model-invocation: true` in `SKILL.md` for Claude Code and
  `policy.allow_implicit_invocation: false` in `agents/openai.yaml` for Codex.
  Their descriptions are short, human-facing summaries.
- **Model-invoked** skills are available to both the human and the model. Omit
  both invocation restrictions. Their descriptions state the situations that
  should trigger the skill automatically.

Keep the Claude and Codex settings aligned. A user-invoked skill in one harness
must not be model-invoked in another.

Dependencies between skills use prose such as “run the `/skill-name` skill.”
Do not couple sibling skills through relative file paths; references and scripts
belong to the skill that owns them.

Claude-specific frontmatter may not be accepted by a generic Agent Skills
validator. Treat that warning as expected only when the matching Codex policy
exists and both settings are intentional.
