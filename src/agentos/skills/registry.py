from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


class SkillEntry(BaseModel):
    name: str
    description: str
    path: str
    scope: str
    last_modified: str
    valid: bool
    errors: list[str]


class SkillRegistry(BaseModel):
    skills: list[SkillEntry]
    warnings: list[str]


class SkillValidation(BaseModel):
    valid: bool
    skill_count: int
    invalid_count: int
    warnings: list[str]
    errors: list[str]


class SkillContent(BaseModel):
    name: str
    description: str
    path: str
    scope: str
    valid: bool
    errors: list[str]
    content: str


def scan_skills(root: Path) -> SkillRegistry:
    entries = []
    for skill_file, scope in _iter_skill_files(root):
        entries.append(_entry_from_file(root, skill_file, scope))
    warnings = _duplicate_warnings(entries)
    registry = SkillRegistry(skills=entries, warnings=warnings)
    agentos_dir = root / ".agentos"
    agentos_dir.mkdir(parents=True, exist_ok=True)
    (agentos_dir / "skill-registry.json").write_text(
        json.dumps(registry.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )
    return registry


def validate_skills(root: Path) -> SkillValidation:
    registry = scan_skills(root)
    errors = []
    for skill in registry.skills:
        for error in skill.errors:
            errors.append(f"{skill.path}: {error}")
    return SkillValidation(
        valid=not errors,
        skill_count=len(registry.skills),
        invalid_count=sum(1 for skill in registry.skills if not skill.valid),
        warnings=registry.warnings,
        errors=errors,
    )


def show_skill(root: Path, skill_name: str) -> SkillContent:
    registry = scan_skills(root)
    for skill in registry.skills:
        if skill.name == skill_name:
            content = (root / skill.path).read_text(encoding="utf-8")
            return SkillContent(
                name=skill.name,
                description=skill.description,
                path=skill.path,
                scope=skill.scope,
                valid=skill.valid,
                errors=skill.errors,
                content=content,
            )
    raise KeyError(f"Skill not found: {skill_name}")


def _iter_skill_files(root: Path) -> list[tuple[Path, str]]:
    locations = [
        (root / "skills", "project"),
        (root / ".agents" / "skills", "codex"),
    ]
    skill_files = []
    for base, scope in locations:
        if not base.exists():
            continue
        for skill_file in sorted(base.glob("**/SKILL.md")):
            skill_files.append((skill_file, scope))
    return skill_files


def _entry_from_file(root: Path, skill_file: Path, scope: str) -> SkillEntry:
    content = skill_file.read_text(encoding="utf-8")
    metadata = _parse_frontmatter(content)
    errors = _validate_metadata(metadata)
    name = metadata.get("name") or skill_file.parent.name
    description = metadata.get("description") or ""
    modified_at = datetime.fromtimestamp(skill_file.stat().st_mtime, tz=UTC).isoformat()
    return SkillEntry(
        name=name,
        description=description,
        path=skill_file.relative_to(root).as_posix(),
        scope=scope,
        last_modified=modified_at,
        valid=not errors,
        errors=errors,
    )


def _validate_metadata(metadata: dict[str, str]) -> list[str]:
    errors = []
    if not metadata.get("name"):
        errors.append("missing name")
    if not metadata.get("description"):
        errors.append("missing description")
    return errors


def _duplicate_warnings(entries: list[SkillEntry]) -> list[str]:
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.name] = counts.get(entry.name, 0) + 1
    return [
        f"Duplicate skill name preserved: {name} ({count} entries)"
        for name, count in sorted(counts.items())
        if count > 1
    ]


def _parse_frontmatter(content: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata
