#!/usr/bin/env python3
"""Build, query, and validate a Hermes Agent skill index.

Usage:
  python3 scripts/skill_index.py build [--skills-dir PATH] [--output-dir PATH]
  python3 scripts/skill_index.py search "query text" [--json]
  python3 scripts/skill_index.py lint [--skills-dir PATH] [--json]
  python3 scripts/skill_index.py stale [--index PATH]
  python3 scripts/skill_index.py install PATH [--category CATEGORY]
  python3 scripts/skill_index.py watch [--interval SECONDS]
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+|[\u4e00-\u9fff]+")
DEFAULT_IGNORE_PATTERNS = [
    "**/.git/**",
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/*backup*/**",
    "**/*bak*/**",
]


@dataclass
class SkillEntry:
    name: str
    title: str
    description: str
    category: str
    triggers: list[str]
    tags: list[str]
    related_skills: list[str]
    path: str
    skill_dir: str
    mtime: float
    sha256: str
    keywords: list[str]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_skills_root() -> Path:
    explicit_skills_dir = os.environ.get("HERMES_SKILLS_DIR")
    if explicit_skills_dir:
        return Path(explicit_skills_dir).expanduser()
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home).expanduser() / "skills"
    return Path.home() / ".hermes" / "skills"


def default_skills_dirs() -> list[Path]:
    return [default_skills_root()]


def parse_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                return parse_list(parsed)
            except Exception:
                pass
        return [part.strip() for part in re.split(r"[,，]", text) if part.strip()]
    return [str(value).strip()]


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    raw = match.group(1)
    body = content[match.end():]
    if yaml is not None:
        loaded = yaml.safe_load(raw) or {}
        return loaded if isinstance(loaded, dict) else {}, body
    data: dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"\'')
    return data, body


def extract_keywords(*parts: str) -> list[str]:
    tokens: set[str] = set()
    for part in parts:
        for token in WORD_RE.findall(part.lower()):
            token = token.strip("-_./:")
            if len(token) >= 2:
                tokens.add(token)
    return sorted(tokens)


def read_ignore_patterns(start_dir: Path) -> list[str]:
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    for candidate in [Path.cwd() / ".skill-router-ignore", start_dir / ".skill-router-ignore", repo_root() / ".skill-router-ignore"]:
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if text and not text.startswith("#"):
                patterns.append(text)
    return patterns


def is_ignored(path: Path, patterns: list[str]) -> bool:
    text = str(path)
    name = path.name
    for pattern in patterns:
        if fnmatch.fnmatch(text, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False


def find_skill_files(skills_dirs: list[Path], ignore_patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for skills_dir in skills_dirs:
        if not skills_dir.exists():
            continue
        for path in skills_dir.rglob("SKILL.md"):
            if not is_ignored(path, ignore_patterns):
                files.append(path)
    return sorted(set(files))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_skill(path: Path) -> SkillEntry | None:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(content)
    name = str(meta.get("name") or path.parent.name).strip()
    if not name:
        return None
    title = str(meta.get("title") or name).strip()
    description = str(meta.get("description") or "").strip()
    category = str(meta.get("category") or (path.parent.parent.name if path.parent.parent.name != "skills" else "")).strip()
    triggers = parse_list(meta.get("triggers"))
    tags = parse_list(meta.get("tags"))
    related_skills = parse_list(meta.get("related_skills"))
    first_headings = " ".join(re.findall(r"^#{1,3}\s+(.+)$", body, flags=re.MULTILINE)[:8])
    keywords = extract_keywords(name, title, description, category, " ".join(triggers), " ".join(tags), first_headings)
    return SkillEntry(
        name=name,
        title=title,
        description=description,
        category=category,
        triggers=triggers,
        tags=tags,
        related_skills=related_skills,
        path=str(path),
        skill_dir=str(path.parent),
        mtime=path.stat().st_mtime,
        sha256=file_sha256(path),
        keywords=keywords,
    )


def build_index(skills_dirs: list[Path], output_dir: Path) -> dict[str, Any]:
    ignore_patterns = read_ignore_patterns(output_dir)
    entries: list[SkillEntry] = []
    for path in find_skill_files(skills_dirs, ignore_patterns):
        entry = read_skill(path)
        if entry:
            entries.append(entry)
    entries.sort(key=lambda item: (item.category, item.name))
    index = {
        "schema_version": 2,
        "generated_by": "skill-router/scripts/skill_index.py",
        "generated_at": int(time.time()),
        "skills_dirs": [str(path) for path in skills_dirs],
        "ignore_patterns": ignore_patterns,
        "count": len(entries),
        "skills": [asdict(entry) for entry in entries],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "skill-index.json"
    md_path = output_dir / "skill-index.md"
    json_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(index), encoding="utf-8")
    return index


def render_markdown(index: dict[str, Any]) -> str:
    lines = ["# Skill Index", "", f"Total skills: {index['count']}", f"Generated at: {index.get('generated_at', '-')}", ""]
    categories: dict[str, list[dict[str, Any]]] = {}
    for skill in index["skills"]:
        categories.setdefault(skill.get("category") or "uncategorized", []).append(skill)
    for category in sorted(categories):
        lines.extend([f"## {category}", ""])
        for skill in categories[category]:
            triggers = ", ".join(skill.get("triggers") or []) or "-"
            lines.append(f"### `{skill['name']}`")
            lines.append(f"- Title: {skill.get('title') or skill['name']}")
            lines.append(f"- Description: {skill.get('description') or '-'}")
            lines.append(f"- Triggers: {triggers}")
            lines.append(f"- SHA256: `{skill.get('sha256', '-')}`")
            lines.append(f"- Path: `{skill.get('path')}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_skill(skill: dict[str, Any], query: str) -> tuple[int, dict[str, Any]]:
    query_lower = query.lower()
    query_tokens = set(extract_keywords(query_lower))
    score = 0
    reasons: dict[str, Any] = {
        "exact_name": False,
        "exact_title": False,
        "matched_triggers": [],
        "matched_tags": [],
        "keyword_overlap": [],
    }
    name = str(skill.get("name", "")).lower()
    title = str(skill.get("title", "")).lower()
    description = str(skill.get("description", "")).lower()
    category = str(skill.get("category", "")).lower()
    if name and name in query_lower:
        score += 100
        reasons["exact_name"] = True
    if title and title in query_lower:
        score += 70
        reasons["exact_title"] = True
    for trigger in skill.get("triggers") or []:
        trigger_lower = str(trigger).lower()
        if trigger_lower and trigger_lower in query_lower:
            score += 60
            reasons["matched_triggers"].append(trigger)
    for tag in skill.get("tags") or []:
        tag_lower = str(tag).lower()
        if tag_lower and tag_lower in query_lower:
            score += 25
            reasons["matched_tags"].append(tag)
    haystack_tokens = set(skill.get("keywords") or [])
    overlap = sorted(query_tokens & haystack_tokens)
    reasons["keyword_overlap"] = overlap
    score += len(overlap) * 8
    for field in [description, category]:
        for token in query_tokens:
            if token in field:
                score += 3
    return score, reasons


def search_index(index: dict[str, Any], query: str, limit: int) -> list[dict[str, Any]]:
    scored = []
    for skill in index.get("skills", []):
        score, reasons = score_skill(skill, query)
        if score > 0:
            item = dict(skill)
            item["score"] = score
            item["match_reasons"] = reasons
            scored.append(item)
    return sorted(scored, key=lambda item: (-item["score"], item.get("name", "")))[:limit]


def lint_entries(entries: list[SkillEntry]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen_names: dict[str, str] = {}
    seen_triggers: dict[str, str] = {}
    vague_triggers = {"code", "debug", "test", "web", "app", "skill", "project", "help", "工具", "项目", "开发", "问题"}
    for entry in entries:
        if entry.name in seen_names:
            issues.append({"severity": "error", "skill": entry.name, "path": entry.path, "message": f"duplicate skill name; first seen at {seen_names[entry.name]}"})
        else:
            seen_names[entry.name] = entry.path
        if not entry.description:
            issues.append({"severity": "error", "skill": entry.name, "path": entry.path, "message": "missing description"})
        elif len(entry.description) < 40:
            issues.append({"severity": "warning", "skill": entry.name, "path": entry.path, "message": "description is very short"})
        if not entry.category:
            issues.append({"severity": "warning", "skill": entry.name, "path": entry.path, "message": "missing category"})
        if not entry.triggers:
            issues.append({"severity": "warning", "skill": entry.name, "path": entry.path, "message": "missing triggers"})
        for trigger in entry.triggers:
            normalized = trigger.lower().strip()
            if normalized in vague_triggers or len(normalized) < 3:
                issues.append({"severity": "warning", "skill": entry.name, "path": entry.path, "message": f"vague trigger: {trigger}"})
            if normalized in seen_triggers and seen_triggers[normalized] != entry.name:
                issues.append({"severity": "warning", "skill": entry.name, "path": entry.path, "message": f"trigger overlaps with {seen_triggers[normalized]}: {trigger}"})
            else:
                seen_triggers[normalized] = entry.name
    return issues


def collect_entries(skills_dirs: list[Path]) -> list[SkillEntry]:
    output_dir = repo_root() / "references"
    ignore_patterns = read_ignore_patterns(output_dir)
    entries: list[SkillEntry] = []
    for path in find_skill_files(skills_dirs, ignore_patterns):
        entry = read_skill(path)
        if entry:
            entries.append(entry)
    return entries


def stale_report(index: dict[str, Any]) -> dict[str, Any]:
    stale: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for skill in index.get("skills", []):
        path = Path(skill.get("path", ""))
        if not path.exists():
            missing.append({"name": skill.get("name"), "path": str(path), "reason": "missing file"})
            continue
        current_hash = file_sha256(path)
        if current_hash != skill.get("sha256"):
            stale.append({"name": skill.get("name"), "path": str(path), "reason": "sha256 changed"})
    return {"is_stale": bool(stale or missing), "stale": stale, "missing": missing}


def snapshot_skill_files(skills_dirs: list[Path]) -> dict[str, str]:
    ignore_patterns = read_ignore_patterns(repo_root() / "references")
    snapshot: dict[str, str] = {}
    for path in find_skill_files(skills_dirs, ignore_patterns):
        if path.exists():
            snapshot[str(path)] = file_sha256(path)
    return snapshot


def install_skill(source: Path, category: str | None, skills_dir: Path, output_dir: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if source.is_file() and source.name == "SKILL.md":
        skill_source_dir = source.parent
    elif source.is_dir():
        skill_source_dir = source
    else:
        raise FileNotFoundError(f"Skill source not found: {source}")
    skill_file = skill_source_dir / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"Missing SKILL.md in: {skill_source_dir}")
    entry = read_skill(skill_file)
    if not entry:
        raise ValueError(f"Invalid skill: {skill_file}")
    target_category = category or entry.category or "uncategorized"
    target_dir = skills_dir.expanduser() / target_category / entry.name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_source_dir, target_dir, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    scan_dirs = default_skills_dirs()
    resolved_skills_dir = skills_dir.expanduser()
    if str(resolved_skills_dir) not in {str(path) for path in scan_dirs}:
        scan_dirs.append(resolved_skills_dir)
    index = build_index(scan_dirs, output_dir)
    return {"installed": entry.name, "target_dir": str(target_dir), "index_count": index["count"], "index": str(output_dir / "skill-index.json")}


def watch_skills(skills_dirs: list[Path], output_dir: Path, interval: float, once: bool) -> int:
    previous = snapshot_skill_files(skills_dirs)
    build_index(skills_dirs, output_dir)
    print(f"Watching {', '.join(str(path) for path in skills_dirs)}")
    while True:
        time.sleep(interval)
        current = snapshot_skill_files(skills_dirs)
        if current != previous:
            index = build_index(skills_dirs, output_dir)
            print(f"Rebuilt index: {index['count']} skills")
            previous = current
            if once:
                return 0
        elif once:
            print("No changes detected")
            return 0


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, query, and validate a Hermes skill index.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--skills-dir", action="append", default=[])
    build_parser.add_argument("--output-dir", default=str(repo_root() / "references"))
    build_parser.add_argument("--json", action="store_true")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--index", default=str(repo_root() / "references" / "skill-index.json"))
    search_parser.add_argument("--limit", type=int, default=3)
    search_parser.add_argument("--json", action="store_true")

    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("--skills-dir", action="append", default=[])
    lint_parser.add_argument("--json", action="store_true")

    stale_parser = subparsers.add_parser("stale")
    stale_parser.add_argument("--index", default=str(repo_root() / "references" / "skill-index.json"))
    stale_parser.add_argument("--json", action="store_true")

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("source", help="Skill directory or SKILL.md to install")
    install_parser.add_argument("--category", default=None)
    install_parser.add_argument("--skills-dir", default=str(default_skills_root()))
    install_parser.add_argument("--output-dir", default=str(repo_root() / "references"))
    install_parser.add_argument("--json", action="store_true")

    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--skills-dir", action="append", default=[])
    watch_parser.add_argument("--output-dir", default=str(repo_root() / "references"))
    watch_parser.add_argument("--interval", type=float, default=5.0)
    watch_parser.add_argument("--once", action="store_true", help="Check once after one interval, rebuild if changed, then exit")

    args = parser.parse_args()
    if args.command == "build":
        skills_dirs = [Path(item).expanduser() for item in args.skills_dir] if args.skills_dir else default_skills_dirs()
        index = build_index(skills_dirs, Path(args.output_dir).expanduser())
        if args.json:
            print_json({"count": index["count"], "index": str(Path(args.output_dir).expanduser() / "skill-index.json")})
        else:
            print(f"Indexed {index['count']} skills")
            print(Path(args.output_dir).expanduser() / "skill-index.json")
        return 0
    if args.command == "search":
        index_path = Path(args.index).expanduser()
        if not index_path.exists():
            print(f"Index not found: {index_path}", file=sys.stderr)
            print("Run: python3 scripts/skill_index.py build", file=sys.stderr)
            return 2
        matches = search_index(load_index(index_path), args.query, args.limit)
        if args.json:
            print_json({"query": args.query, "matches": matches})
        else:
            for item in matches:
                reasons = item.get("match_reasons", {})
                overlap = ",".join(reasons.get("keyword_overlap") or [])
                print(f"{item['score']:>3}  {item['name']}  - {item.get('description', '')}")
                if overlap:
                    print(f"     keywords: {overlap}")
        return 0
    if args.command == "lint":
        skills_dirs = [Path(item).expanduser() for item in args.skills_dir] if args.skills_dir else default_skills_dirs()
        issues = lint_entries(collect_entries(skills_dirs))
        if args.json:
            print_json({"issue_count": len(issues), "issues": issues})
        else:
            if not issues:
                print("No lint issues found")
            for issue in issues:
                print(f"{issue['severity'].upper()} {issue['skill']}: {issue['message']} ({issue['path']})")
        return 1 if any(issue["severity"] == "error" for issue in issues) else 0
    if args.command == "stale":
        index_path = Path(args.index).expanduser()
        if not index_path.exists():
            print(f"Index not found: {index_path}", file=sys.stderr)
            return 2
        report = stale_report(load_index(index_path))
        if args.json:
            print_json(report)
        else:
            print("STALE" if report["is_stale"] else "FRESH")
            for item in report["stale"] + report["missing"]:
                print(f"{item['name']}: {item['reason']} ({item['path']})")
        return 1 if report["is_stale"] else 0
    if args.command == "install":
        try:
            result = install_skill(Path(args.source), args.category, Path(args.skills_dir), Path(args.output_dir).expanduser())
        except Exception as exc:
            print(f"Install failed: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print_json(result)
        else:
            print(f"Installed {result['installed']} -> {result['target_dir']}")
            print(f"Rebuilt index: {result['index_count']} skills")
            print(result["index"])
        return 0
    if args.command == "watch":
        skills_dirs = [Path(item).expanduser() for item in args.skills_dir] if args.skills_dir else default_skills_dirs()
        return watch_skills(skills_dirs, Path(args.output_dir).expanduser(), args.interval, args.once)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
