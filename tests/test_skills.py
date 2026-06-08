import json

from agentos.skills.registry import scan_skills, show_skill, validate_skills


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
    assert registry.skills[0].scope == "project"
    assert registry.skills[0].valid is True
    assert registry.skills[0].errors == []
    assert registry.skills[0].last_modified
    registry_path = tmp_path / ".agentos" / "skill-registry.json"
    assert registry_path.exists()
    registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry_data["skills"][0]["name"] == "memory-capture"


def test_scan_codex_style_agent_skills(tmp_path):
    skill_dir = tmp_path / ".agents" / "skills" / "sqlite-memory"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: sqlite-memory
description: Use when working on local SQLite memory behavior.
---

# SQLite Memory

Read this only when explicitly showing the skill.
""",
        encoding="utf-8",
    )

    registry = scan_skills(tmp_path)

    assert len(registry.skills) == 1
    assert registry.skills[0].scope == "codex"
    assert registry.skills[0].path == ".agents/skills/sqlite-memory/SKILL.md"


def test_invalid_skill_reports_errors(tmp_path):
    skill_dir = tmp_path / ".agents" / "skills" / "invalid"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: invalid\n---\n", encoding="utf-8")

    registry = scan_skills(tmp_path)
    validation = validate_skills(tmp_path)

    assert registry.skills[0].valid is False
    assert "missing description" in registry.skills[0].errors
    assert validation.valid is False
    assert validation.invalid_count == 1


def test_duplicate_skills_are_preserved_and_warned(tmp_path):
    project_dir = tmp_path / "skills" / "duplicate"
    codex_dir = tmp_path / ".agents" / "skills" / "duplicate"
    project_dir.mkdir(parents=True)
    codex_dir.mkdir(parents=True)
    for directory in (project_dir, codex_dir):
        (directory / "SKILL.md").write_text(
            "---\nname: duplicate\ndescription: Duplicate trigger.\n---\n",
            encoding="utf-8",
        )

    registry = scan_skills(tmp_path)

    assert [skill.name for skill in registry.skills] == ["duplicate", "duplicate"]
    assert len(registry.warnings) == 1
    assert "Duplicate skill name" in registry.warnings[0]


def test_show_skill_loads_full_content_only_on_request(tmp_path):
    skill_dir = tmp_path / ".agents" / "skills" / "safety-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: safety-review
description: Use before risky command or file operations.
---

# Safety Review

Full checklist content.
""",
        encoding="utf-8",
    )

    shown = show_skill(tmp_path, "safety-review")

    assert shown.name == "safety-review"
    assert "# Safety Review" in shown.content
