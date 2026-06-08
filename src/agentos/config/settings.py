from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class UISettings(BaseModel):
    show_banner: bool = True
    open_dashboard_on_start: bool = True
    theme: str = "zellij-neutral"
    compact_mode: str = "auto"


class AgentOSConfig(BaseModel):
    ui: UISettings = UISettings()


DEFAULT_CONFIG = AgentOSConfig()


def create_default_config(root: Path) -> Path:
    path = _config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_config(path, DEFAULT_CONFIG)
    return path


def load_config(root: Path) -> AgentOSConfig:
    path = create_default_config(root)
    return read_config(path)


def read_config(path: Path) -> AgentOSConfig:
    if not path.exists():
        return DEFAULT_CONFIG.model_copy(deep=True)
    return AgentOSConfig(ui=UISettings(**_parse_ui_block(path.read_text(encoding="utf-8"))))


def write_config(path: Path, config: AgentOSConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_config(config), encoding="utf-8")


def set_theme(root: Path, theme_name: str) -> AgentOSConfig:
    path = create_default_config(root)
    config = read_config(path)
    config.ui.theme = theme_name
    write_config(path, config)
    return config


def set_banner_visibility(root: Path, visible: bool) -> AgentOSConfig:
    path = create_default_config(root)
    config = read_config(path)
    config.ui.show_banner = visible
    write_config(path, config)
    return config


def _config_path(root: Path) -> Path:
    return root / ".agentos" / "config.yaml"


def _render_config(config: AgentOSConfig) -> str:
    show_banner = _bool_text(config.ui.show_banner)
    open_dashboard = _bool_text(config.ui.open_dashboard_on_start)
    return "\n".join(
        [
            "ui:",
            f"  show_banner: {show_banner}",
            f"  open_dashboard_on_start: {open_dashboard}",
            f"  theme: {config.ui.theme}",
            f"  compact_mode: {config.ui.compact_mode}",
            "",
        ]
    )


def _parse_ui_block(content: str) -> dict[str, object]:
    values: dict[str, object] = DEFAULT_CONFIG.ui.model_dump()
    in_ui = False
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" ") and raw_line.strip() == "ui:":
            in_ui = True
            continue
        if not in_ui:
            continue
        if not raw_line.startswith(" "):
            break
        if ":" not in raw_line:
            continue
        key, value = raw_line.strip().split(":", 1)
        values[key.strip()] = _parse_scalar(value.strip())
    return values


def _parse_scalar(value: str) -> object:
    normalized = value.strip().strip('"').strip("'")
    if normalized.lower() == "true":
        return True
    if normalized.lower() == "false":
        return False
    return normalized


def _bool_text(value: bool) -> str:
    return "true" if value else "false"
