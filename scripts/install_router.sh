#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
SKILLS_ROOT="${HERMES_SKILLS_DIR:-$HERMES_ROOT/skills}"
TARGET_DIR="$SKILLS_ROOT/workflow/skill-router"

mkdir -p "$(dirname "$TARGET_DIR")"

if [ "$(realpath -m "$SOURCE_DIR")" != "$(realpath -m "$TARGET_DIR")" ]; then
  rm -rf "$TARGET_DIR"
  cp -R "$SOURCE_DIR" "$TARGET_DIR"
fi

rm -rf "$TARGET_DIR/scripts/__pycache__"
chmod +x "$TARGET_DIR/scripts/skill_index.py" "$TARGET_DIR/scripts/install_skill.sh" "$TARGET_DIR/scripts/install_router.sh"

python3 "$TARGET_DIR/scripts/skill_index.py" build --skills-dir "$SKILLS_ROOT" --output-dir "$TARGET_DIR/references"

echo "Installed skill-router -> $TARGET_DIR"
echo "Initial skill index -> $TARGET_DIR/references/skill-index.json"
