# Routing Rules

## Match priority

1. Exact skill name mentioned by the user.
2. Project or product name match.
3. Tool/provider/framework/API match.
4. Trigger phrase match.
5. Description/category match.
6. Weak keyword overlap.

## Selection rules

- Load the narrowest skill first.
- Load a second skill only if it supplies a different required capability.
- Do not load multiple skills that explain the same task unless one explicitly references the other.
- If a project-specific skill exists, it usually outranks a generic framework skill.

## Maintenance rules

- Rebuild `references/skill-index.json` after every skill add/edit/delete.
- If a search result is wrong, improve the target skill metadata first.
- If two skills compete for the same query, add anti-triggers or narrow descriptions.
- If one skill becomes too large, split unrelated workflows into separate skills and keep router metadata precise.

## Suggested anti-trigger examples

- SEO skills: do not use for general bug fixing unless the bug affects SEO behavior.
- Video skills: do not use for static diagrams or Markdown docs.
- Image skills: do not use for video animation unless paired with a video skill.
- Hermes configuration skills: do not use for application-level payment or business provider configuration unless Hermes itself is being configured.
