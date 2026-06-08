---
name: skill-router
title: Skill Router
description: Build and maintain an index of installed Hermes Agent skills, then route user requests to the smallest correct set of skills before doing work.
triggers: ["skill routing", "skill router", "skill index", "skill 命中率", "技能路由", "技能索引", "选择正确skill", "新增skill索引", "管理很多skill"]
category: workflow
---

# Skill Router

Use this skill as a bootstrap skill router when an agent needs to decide whether any other Hermes Agent skill should be loaded. This skill is most effective when the agent's global instructions require it to consult `skill-router` before selecting task-specific skills.

## What this skill provides

- A bootstrap routing rule that can be placed in an agent's global/system instructions.
- A repeatable routing workflow for choosing the smallest correct set of skills.
- A local index format generated from installed skill metadata.
- Scripts to build, update, inspect, and search the index.
- Maintenance rules for newly added skills.

## Important: automatic triggering

This skill does not automatically intercept conversations by being installed alone. To make it automatic, add the bootstrap instruction from `templates/bootstrap-system-prompt.md` to the agent's global/system instructions.

Without that global instruction, the router only activates when the normal skill matcher chooses `skill-router`. With the bootstrap instruction, the agent consults the skill index before loading task-specific skills.

## Required behavior

Before substantial work, if this skill is loaded:

1. Inspect the generated index at `references/skill-index.json` when available.
2. Match the user request against indexed `name`, `title`, `description`, `triggers`, `category`, `tags`, `related_skills`, and extracted keywords.
3. Prefer specific/project/tool skills over broad/generic skills.
4. Load only the smallest necessary skill set.
5. If no match is strong, continue without forcing a skill and report the missing coverage only when useful.
6. If a new skill was installed or edited, refresh the index with `scripts/skill_index.py build`.

## First install / refresh

Preferred first install from the repository root:

```bash
./scripts/install_router.sh
```

This copies `skill-router` into `~/.hermes/skills/workflow/skill-router` and immediately builds an initial index from all already-installed Hermes skills.

From the installed skill directory, refresh manually with:

```bash
python3 scripts/skill_index.py build
```

This scans installed Hermes skills and writes:

- `references/skill-index.json`
- `references/skill-index.md`

The generated JSON includes each skill's `mtime` and `sha256`, so stale indexes can be detected later.

By default it scans:

- `$HERMES_HOME/skills`
- `~/.hermes/skills`

You can override the scan root:

```bash
python3 scripts/skill_index.py build --skills-dir ~/.hermes/skills
```

## Add or update a skill

Preferred method: install skills through the router so the index is rebuilt automatically:

```bash
python3 scripts/skill_index.py install /path/to/new-skill
python3 scripts/skill_index.py install /path/to/new-skill --category development
```

This copies the skill into `~/.hermes/skills/<category>/<name>/` and immediately rebuilds the router index.

If skills are installed by another tool or copied manually, either run:

```bash
python3 scripts/skill_index.py build
```

or keep a watcher running:

```bash
python3 scripts/skill_index.py watch
```

The watcher monitors installed `SKILL.md` files and rebuilds the index whenever a skill is added, edited, renamed, or deleted.

## Search the index manually

```bash
python3 scripts/skill_index.py search "Hermes custom provider config"
python3 scripts/skill_index.py search "locallife 支付 微信小程序"
python3 scripts/skill_index.py search "生成视频 Remotion"
python3 scripts/skill_index.py search "Hermes custom provider config" --json
```

Use `--json` when another tool, script, or agent workflow needs machine-readable routing results.

## Check index freshness

```bash
python3 scripts/skill_index.py stale
python3 scripts/skill_index.py stale --json
```

If `stale` reports changed or missing files, rebuild the index.

## Lint skill metadata

```bash
python3 scripts/skill_index.py lint
python3 scripts/skill_index.py lint --json
```

Use lint results to improve weak descriptions, missing triggers, missing categories, duplicate names, and overlapping triggers.

## Ignore scan paths

Create `.skill-router-ignore` in this skill root or the current working directory to exclude backup, temporary, generated, or third-party directories from scanning. Glob patterns are supported.

## Routing workflow

1. Identify intent:
   - configure/setup/troubleshoot a tool
   - edit/debug code
   - operate on a named project
   - generate image/video/audio/media
   - create diagrams/docs/visualizations
   - audit SEO/UX/product content
   - manage skills or agent behavior
2. Identify hard context:
   - active workspace
   - project name
   - framework/platform/provider/API/tool
   - requested output artifact
   - explicit skill name if mentioned
3. Search the index using the user request plus hard context.
4. Pick candidates:
   - exact skill name match: strongest
   - project/tool/provider match: strong
   - trigger phrase match: strong
   - description/category match: medium
   - broad keyword match only: weak
5. Exclude false positives:
   - media skill should not be used for static docs unless video/image output is requested
   - SEO skill should not be used for general code debugging
   - generic development skill should not override a project-specific skill
   - Hermes provider skill should not be used for application payment providers unless Hermes config is involved
6. Load the best skill first; add related skills only when they cover a separate required dimension.

## Skill metadata quality standard

Every skill intended to route well should include:

- precise `name`
- precise `description`
- explicit `triggers`
- `category`
- optional `tags`
- optional `related_skills`
- clear “Use this skill when...” section
- clear anti-triggers or “Do not use when...” section for overlapping domains

## Repository files

- `scripts/skill_index.py`: scans installed skills and builds/searches the index.
- `references/skill-index.json`: generated machine-readable index.
- `references/skill-index.md`: generated human-readable index.
- `templates/SKILL.md.template`: recommended template for routable skills.
- `references/routing-rules.md`: detailed matching and maintenance rules.

## Pitfalls

- A large number of vague skills lowers hit rate. Fix metadata before blaming the router.
- Duplicate skills with overlapping descriptions cause unstable routing. Merge or narrow them.
- Stale generated indexes can miss newly added skills. Rebuild after changes.
- Do not blindly load all plausible skills. Too many loaded skills can pollute context and reduce accuracy.
