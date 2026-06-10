from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from agentos.models.config import load_model_config
from agentos.models.effort import validate_effort
from agentos.models.schemas import ModelEffort

ROUTE_NAMES = {
    "default_chat",
    "coding",
    "sdd_explore",
    "sdd_design",
    "sdd_verify",
    "refiner_analyze",
    "safety_review",
}


class ModelRoute(BaseModel):
    model_profile: str | None = None
    effort: ModelEffort


class ModelRoutingConfig(BaseModel):
    routes: dict[str, ModelRoute]


def create_default_routing_config(root: Path) -> Path:
    path = routing_config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_routing_config(path, default_routing_config())
    return path


def load_routing_config(root: Path) -> ModelRoutingConfig:
    path = create_default_routing_config(root)
    return read_routing_config(path)


def read_routing_config(path: Path) -> ModelRoutingConfig:
    if not path.exists():
        return default_routing_config()
    return _parse_routing_config(path.read_text(encoding="utf-8"))


def write_routing_config(path: Path, config: ModelRoutingConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_routing_config(config), encoding="utf-8")


def default_routing_config() -> ModelRoutingConfig:
    return ModelRoutingConfig(
        routes={
            "default_chat": ModelRoute(effort="medium"),
            "coding": ModelRoute(effort="high"),
            "sdd_explore": ModelRoute(effort="medium"),
            "sdd_design": ModelRoute(effort="high"),
            "sdd_verify": ModelRoute(effort="max"),
            "refiner_analyze": ModelRoute(effort="high"),
            "safety_review": ModelRoute(effort="max"),
        }
    )


def routing_config_path(root: Path) -> Path:
    return root / ".agentos" / "model-routing.yaml"


def resolve_route(root: Path, route_name: str) -> ModelRoute:
    config = load_routing_config(root)
    if route_name not in config.routes:
        raise KeyError(f"Unknown model route: {route_name}")
    return config.routes[route_name]


def set_route(
    root: Path,
    route_name: str,
    *,
    model_profile: str | None,
    effort: str,
) -> ModelRoutingConfig:
    if route_name not in ROUTE_NAMES:
        raise KeyError(f"Unknown model route: {route_name}")
    effort_value = validate_effort(effort)
    if model_profile is not None:
        _validate_model_profile(root, model_profile)
    path = create_default_routing_config(root)
    config = read_routing_config(path)
    config.routes[route_name] = ModelRoute(model_profile=model_profile, effort=effort_value)
    write_routing_config(path, config)
    return config


def effective_effort(
    root: Path,
    route_name: str,
    explicit_effort: str | None = None,
) -> ModelEffort:
    if explicit_effort:
        return validate_effort(explicit_effort)
    return resolve_route(root, route_name).effort


def effective_model_profile(
    root: Path,
    route_name: str,
    explicit_model_profile: str | None = None,
) -> str | None:
    if explicit_model_profile:
        return explicit_model_profile
    return resolve_route(root, route_name).model_profile


def _validate_model_profile(root: Path, model_profile: str) -> None:
    config = load_model_config(root)
    if model_profile not in {profile.name for profile in config.model_profiles}:
        raise KeyError(f"Unknown model profile: {model_profile}")


def _render_routing_config(config: ModelRoutingConfig) -> str:
    lines = ["routes:"]
    for route_name in sorted(config.routes):
        route = config.routes[route_name]
        lines.append(f"  {route_name}:")
        lines.append(f"    model_profile: {_render_scalar(route.model_profile)}")
        lines.append(f"    effort: {route.effort}")
    lines.append("")
    return "\n".join(lines)


def _parse_routing_config(content: str) -> ModelRoutingConfig:
    routes: dict[str, dict[str, Any]] = {}
    current_route: str | None = None
    in_routes = False
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()
        if not raw_line.startswith(" ") and stripped == "routes:":
            in_routes = True
            continue
        if not in_routes:
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    ") and stripped.endswith(":"):
            current_route = stripped[:-1]
            routes[current_route] = {}
            continue
        if current_route and raw_line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            routes[current_route][key.strip()] = _parse_scalar(value.strip())
    merged = default_routing_config().model_dump(mode="json")["routes"]
    for route_name, route_data in routes.items():
        if route_name not in ROUTE_NAMES:
            raise KeyError(f"Unknown model route: {route_name}")
        route_effort = str(route_data.get("effort") or merged[route_name]["effort"])
        merged[route_name] = {
            "model_profile": route_data.get("model_profile"),
            "effort": validate_effort(route_effort),
        }
    return ModelRoutingConfig(routes={key: ModelRoute(**value) for key, value in merged.items()})


def _render_scalar(value: object) -> str:
    if value is None:
        return "null"
    return str(value)


def _parse_scalar(value: str) -> object:
    normalized = value.strip().strip('"').strip("'")
    if normalized.lower() == "null":
        return None
    return normalized
