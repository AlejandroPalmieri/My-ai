from __future__ import annotations

from pydantic import BaseModel


class ThemePalette(BaseModel):
    background: str
    surface: str
    panel: str
    border: str
    border_active: str
    primary: str
    secondary: str
    text: str
    muted: str
    success: str
    warning: str
    danger: str


class Theme(BaseModel):
    name: str
    description: str
    palette: ThemePalette

    def style(self, color_name: str, *, bold: bool = False) -> str:
        color = getattr(self.palette, color_name)
        return f"bold {color}" if bold else color


ZELLIJ_NEUTRAL = Theme(
    name="zellij-neutral",
    description="Neutral dark pane-based terminal theme.",
    palette=ThemePalette(
        background="#101418",
        surface="#161B22",
        panel="#1E252E",
        border="#3A4A55",
        border_active="#7AA89F",
        primary="#9DD6C5",
        secondary="#88A2B6",
        text="#D8DEE9",
        muted="#8A99A8",
        success="#A3BE8C",
        warning="#EBCB8B",
        danger="#BF616A",
    ),
)

THEMES = {ZELLIJ_NEUTRAL.name: ZELLIJ_NEUTRAL}


def load_theme(name: str = "zellij-neutral") -> Theme:
    try:
        return THEMES[name]
    except KeyError as error:
        raise KeyError(f"Unknown UI theme: {name}") from error


def list_themes() -> list[Theme]:
    return sorted(THEMES.values(), key=lambda theme: theme.name)
