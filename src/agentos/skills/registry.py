from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class SkillEntry(BaseModel):
    name: str
    description: str
    path: str


class SkillRegistry(BaseModel):
    skills: list[SkillEntry]


def scan_skills(root: Path) -> SkillRegistry:
    entries = []
    for skill_file in sorted((root / "skills").glob("**/SKILL.md")):
        metadata = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        name = metadata.get("name") or skill_file.parent.name
        description = metadata.get("description") or ""
        entries.append(
            SkillEntry(
                name=name,
                description=description,
                path=skill_file.relative_to(root).as_posix(),
            )
        )
    registry = SkillRegistry(skills=entries)
    agentos_dir = root / ".agentos"
    agentos_dir.mkdir(parents=True, exist_ok=True)
    (agentos_dir / "skill-registry.json").write_text(
        json.dumps(registry.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )
    return registry


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
