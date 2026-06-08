from agentos.services.local import (
    LocalPolicyService,
    LocalRefinerService,
    LocalSDDService,
    LocalSkillRegistryService,
    LocalStrategicBrainService,
    LocalTechnicalMemoryService,
)


def test_local_services_expose_mcp_ready_boundaries(tmp_path):
    memory = LocalTechnicalMemoryService(tmp_path)
    added = memory.add_memory(
        project="demo",
        title="Boundary",
        kind="note",
        content="MCP-ready service boundary",
        tags=["mcp"],
    )

    sdd = LocalSDDService(tmp_path)
    change = sdd.create_change("service-boundaries")

    skills_dir = tmp_path / "skills" / "demo"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill.\n---\n",
        encoding="utf-8",
    )
    skills = LocalSkillRegistryService(tmp_path).scan()

    policy = LocalPolicyService(tmp_path)

    assert added.title == "Boundary"
    assert memory.search_memories("MCP-ready")[0].id == added.id
    assert change.name == "service-boundaries"
    assert skills.skills[0].name == "demo"
    assert not policy.check_path(".env").allowed
    assert "Phase 2 service boundary stub" in LocalStrategicBrainService().synthesize("roadmap")
    assert "Phase 2 service boundary stub" in LocalRefinerService().analyze_trace(
        tmp_path / "trace.jsonl"
    )
