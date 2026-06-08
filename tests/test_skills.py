import json

from agentos.skills.registry import scan_skills


def test_scan_skills_writes_registry(tmp_path):
    skill_dir = tmp_path / "skills" / "memory"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: memory-capture
description: Capture technical decisions.
---

# Memory Capture
""",
        encoding="utf-8",
    )

    registry = scan_skills(tmp_path)

    assert len(registry.skills) == 1
    assert registry.skills[0].name == "memory-capture"
    assert registry.skills[0].description == "Capture technical decisions."
    registry_path = tmp_path / ".agentos" / "skill-registry.json"
    assert registry_path.exists()
    registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry_data["skills"][0]["name"] == "memory-capture"
