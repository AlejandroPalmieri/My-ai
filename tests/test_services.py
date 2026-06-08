from pathlib import Path

from agentos.services.container import ServiceContainer, create_service_container
from agentos.services.interfaces import (
    PolicyService,
    ProfileService,
    RefinerService,
    SDDService,
    SkillRegistryService,
    StrategicBrainService,
    TechnicalMemoryService,
    TraceService,
)
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


def test_service_container_initializes_all_local_services(tmp_path):
    container = create_service_container(tmp_path)

    assert isinstance(container, ServiceContainer)
    assert container.root == tmp_path
    assert isinstance(container.memory, TechnicalMemoryService)
    assert isinstance(container.sdd, SDDService)
    assert isinstance(container.skills, SkillRegistryService)
    assert isinstance(container.policies, PolicyService)
    assert isinstance(container.traces, TraceService)
    assert isinstance(container.profiles, ProfileService)
    assert isinstance(container.strategic_brain, StrategicBrainService)
    assert isinstance(container.refiner, RefinerService)


def test_profile_and_trace_services_are_local_first(tmp_path):
    container = create_service_container(tmp_path)

    profile = container.profiles.load()
    event = container.traces.start("service.test")
    container.traces.complete(
        "service.test",
        trace=event,
        payload={"profile": profile.active_profile},
    )

    dates = container.traces.list_dates()

    assert profile.active_profile == "default"
    assert dates
    assert container.traces.tail(limit=1)[0].command == "service.test"


def test_service_stubs_explain_future_integration_boundaries(tmp_path):
    container = create_service_container(tmp_path)

    synthesis = container.strategic_brain.synthesize("roadmap")
    analysis = container.refiner.analyze_trace(Path("trace.jsonl"))

    assert "TODO" in synthesis
    assert "GBrain" in synthesis
    assert "TODO" in analysis
    assert "Continual Harness" in analysis
