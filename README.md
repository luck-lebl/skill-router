# Skill Router for Hermes Agent

`skill-router` is a Hermes Agent skill that helps agents choose the correct skill when many skills are installed.

It scans installed skills, builds a local index, and provides routing rules for selecting the smallest correct skill set.

## Features

- Scans `$HERMES_HOME/skills` and `~/.hermes/skills`
- Extracts frontmatter metadata from every `SKILL.md`
- Generates `references/skill-index.json`
- Generates `references/skill-index.md`
- Supports `.skill-router-ignore` scan exclusions
- Records `mtime` and `sha256` for stale-index detection
- Provides manual search with scoring and match reasons
- Supports JSON output for automation
- Provides metadata linting for routing quality
- Includes a template for routable skills

## Install

Preferred first install:

```bash
cd skill-router
./scripts/install_router.sh
```

This installs `skill-router` into `~/.hermes/skills/workflow/skill-router` and immediately scans all already-installed skills to create the initial router index:

- `~/.hermes/skills/workflow/skill-router/references/skill-index.json`
- `~/.hermes/skills/workflow/skill-router/references/skill-index.md`

Manual install alternative:

```bash
mkdir -p ~/.hermes/skills/workflow
cp -R skill-router ~/.hermes/skills/workflow/skill-router
cd ~/.hermes/skills/workflow/skill-router
python3 scripts/skill_index.py build
```

## Enable automatic routing

Installing this skill alone does not make it intercept every conversation. To make it automatic, add the bootstrap instruction in `templates/bootstrap-system-prompt.md` to your agent's global/system instructions.

Minimal bootstrap instruction:

```text
Before selecting task-specific skills, use `skill-router` as the bootstrap router whenever installed skills may be relevant. Search its generated index, choose the smallest correct skill set, then load only those skills. Do not wait for the user to explicitly request `skill-router`.
```

After this, users do not need to mention `skill-router`; it becomes an internal preflight step for skill selection.

## Usage

Search manually:

```bash
python3 scripts/skill_index.py search "configure Hermes custom provider"
python3 scripts/skill_index.py search "configure Hermes custom provider" --json
```

Check whether the generated index is stale:

```bash
python3 scripts/skill_index.py stale
```

Lint installed skill metadata:

```bash
python3 scripts/skill_index.py lint
python3 scripts/skill_index.py lint --json
```

After adding or editing a skill:

```bash
python3 scripts/skill_index.py build
```

Install a new skill and automatically refresh the index:

```bash
python3 scripts/skill_index.py install /path/to/new-skill
python3 scripts/skill_index.py install /path/to/new-skill --category development
```

If skills may be copied by other tools, run a watcher:

```bash
python3 scripts/skill_index.py watch
```

Use `.skill-router-ignore` to exclude backup, temporary, or third-party directories from scanning.

## Notes

This skill improves routing quality, but it cannot fully compensate for vague skill metadata. For best results, each skill should include precise `description`, `triggers`, `category`, and anti-trigger guidance.
