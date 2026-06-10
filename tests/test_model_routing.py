from typer.testing import CliRunner

from agentos.agents.registry import AgentRuntimeRegistry
from agentos.cli.app import app
from agentos.models.client import chat_once
from agentos.models.effort import EFFORT_PROFILES, get_effort_profile
from agentos.models.routing import (
    create_default_routing_config,
    load_routing_config,
    resolve_route,
    set_route,
)
from agentos.ui.dashboard import collect_dashboard_data

runner = CliRunner()


def test_effort_definitions():
    assert set(EFFORT_PROFILES) == {"low", "medium", "high", "max"}
    high = get_effort_profile("high")

    assert high.label == "high"
    assert high.default_temperature >= 0
    assert high.default_max_output_tokens > 0
    assert "architecture" in high.intended_use.lower()


def test_route_config_creation_and_defaults(tmp_path):
    path = create_default_routing_config(tmp_path)
    config = load_routing_config(tmp_path)

    assert path == tmp_path / ".agentos" / "model-routing.yaml"
    assert path.exists()
    assert config.routes["default_chat"].effort == "medium"
    assert config.routes["coding"].effort == "high"
    assert config.routes["sdd_verify"].effort == "max"


def test_route_set_and_resolve(tmp_path):
    updated = set_route(
        tmp_path,
        "default_chat",
        model_profile="ollama-local",
        effort="high",
    )
    resolved = resolve_route(tmp_path, "default_chat")

    assert updated.routes["default_chat"].model_profile == "ollama-local"
    assert resolved.model_profile == "ollama-local"
    assert resolved.effort == "high"


def test_models_effort_and_route_cli(tmp_path):
    effort_list = runner.invoke(app, ["models", "effort", "list", "--root", str(tmp_path)])
    effort_show = runner.invoke(
        app,
        ["models", "effort", "show", "max", "--root", str(tmp_path)],
    )
    route_list = runner.invoke(app, ["models", "route", "list", "--root", str(tmp_path)])
    route_set = runner.invoke(
        app,
        [
            "models",
            "route",
            "set",
            "default_chat",
            "--model",
            "ollama-local",
            "--effort",
            "high",
            "--root",
            str(tmp_path),
        ],
    )

    assert effort_list.exit_code == 0
    assert "low" in effort_list.output
    assert "max" in effort_list.output
    assert effort_show.exit_code == 0
    assert "safety review" in effort_show.output.lower()
    assert route_list.exit_code == 0
    assert "default_chat" in route_list.output
    assert route_set.exit_code == 0
    assert "default_chat" in route_set.output
    assert "ollama-local" in route_set.output


def test_chat_uses_route_default_and_effort_override(tmp_path):
    default_response = chat_once(tmp_path, message="route default")
    override_response = chat_once(tmp_path, message="override", effort="max")

    assert default_response.effort == "medium"
    assert "medium" in default_response.text
    assert override_response.effort == "max"
    assert "max" in override_response.text


def test_agent_start_defaults_effort_from_coding_route(tmp_path):
    agent = AgentRuntimeRegistry(tmp_path).start_agent(
        name="Coder",
        role="implementation",
        current_task="Use routing effort",
        model_profile="local-stub",
    )

    assert agent.effort == "high"


def test_agent_cli_effort_override(tmp_path):
    result = runner.invoke(
        app,
        [
            "agents",
            "start",
            "--name",
            "Quick",
            "--role",
            "triage",
            "--task",
            "Use explicit low effort",
            "--model",
            "local-stub",
            "--effort",
            "low",
            "--root",
            str(tmp_path),
        ],
    )
    agent = AgentRuntimeRegistry(tmp_path).list_agents()[0]

    assert result.exit_code == 0
    assert agent.effort == "low"


def test_dashboard_shows_effective_effort_from_route(tmp_path):
    set_route(tmp_path, "default_chat", model_profile="local-stub", effort="high")

    data = collect_dashboard_data(tmp_path)

    assert data.runtime.model_status.effort == "high"
