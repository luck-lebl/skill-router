# Skill Router Bootstrap System Prompt

Add this block to the agent's global/system instructions if you want `skill-router` to act as the automatic entry point before task-specific skill selection.

```text
# Skill routing bootstrap
Before loading any task-specific skill, decide whether the user request may benefit from installed skills. If yes, consult the installed `skill-router` skill or its generated index first.

Routing procedure:
1. If `skill-router` is available, load it before loading task-specific skills when multiple skills may match, when the correct skill is unclear, or when the task mentions a known project/tool/provider/media/documentation domain.
2. If direct file access to the skill index is available, inspect `~/.hermes/skills/workflow/skill-router/references/skill-index.json` and match the user request against `name`, `title`, `description`, `triggers`, `category`, `tags`, `related_skills`, and `keywords`.
3. Select the smallest correct set of task-specific skills. Prefer exact name, project-specific, tool-specific, and trigger matches over broad keyword matches.
4. Load the selected task-specific skill or skills, then continue the task.
5. If no skill is a strong match, proceed without a skill instead of forcing a weak match.
6. When installing a new skill from a local directory, prefer `python3 ~/.hermes/skills/workflow/skill-router/scripts/skill_index.py install /path/to/skill` so the skill is copied into the skills directory and the index is rebuilt automatically.
7. If a skill is added, edited, renamed, deleted, or installed by another tool, rebuild the index with `python3 ~/.hermes/skills/workflow/skill-router/scripts/skill_index.py build` before routing when tools are available.
8. For long-lived agents, optionally run `python3 ~/.hermes/skills/workflow/skill-router/scripts/skill_index.py watch` in the background so the router index updates when installed skills change.

Do not require the user to say “load skill-router”. The router is an internal preflight step for skill selection.
```

## Minimal version

```text
Before selecting task-specific skills, use `skill-router` as the bootstrap router whenever installed skills may be relevant. Search its generated index, choose the smallest correct skill set, then load only those skills. Do not wait for the user to explicitly request `skill-router`.
```
