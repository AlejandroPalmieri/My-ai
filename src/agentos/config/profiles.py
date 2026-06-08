from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ProfileSpec(BaseModel):
    description: str
    focus: list[str]


class ProjectProfile(BaseModel):
    active_profile: str
    profiles: dict[str, ProfileSpec]

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"active_profile: {self.active_profile}", "profiles:"]
        for name, profile in self.profiles.items():
            lines.append(f"  {name}:")
            lines.append(f"    description: {profile.description}")
            lines.append("    focus:")
            for item in profile.focus:
                lines.append(f"      - {item}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> ProjectProfile:
        return _parse_profile(path.read_text(encoding="utf-8"))


DEFAULT_PROFILES = {
    "godot": ProfileSpec(
        description="Game development workflows centered on Godot projects.",
        focus=["gameplay systems", "assets", "tool scripts", "playtesting"],
    ),
    "bioinformatics": ProfileSpec(
        description="Local analysis workflows for biological datasets and pipelines.",
        focus=["pipelines", "reproducibility", "data provenance", "notebooks"],
    ),
    "usmle": ProfileSpec(
        description="Study and retrieval workflows for USMLE preparation.",
        focus=["question review", "spaced repetition", "clinical reasoning", "weak areas"],
    ),
    "neocircuit": ProfileSpec(
        description="Neocircuit research and knowledge synthesis workspace.",
        focus=["entities", "hypotheses", "experiments", "synthesis"],
    ),
    "data-science": ProfileSpec(
        description="Data science project workflows from exploration to reporting.",
        focus=["datasets", "experiments", "models", "reports"],
    ),
}


def create_default_profile(root: Path) -> Path:
    path = root / ".agentos" / "profile.yaml"
    if not path.exists():
        ProjectProfile(active_profile="godot", profiles=DEFAULT_PROFILES).write(path)
    return path


def load_profile(path: Path) -> ProjectProfile:
    return ProjectProfile.read(path)


def _parse_profile(content: str) -> ProjectProfile:
    active_profile = ""
    profiles: dict[str, ProfileSpec] = {}
    current_name: str | None = None
    current_description = ""
    current_focus: list[str] = []
    in_focus = False

    def flush_current() -> None:
        nonlocal current_name, current_description, current_focus
        if current_name is not None:
            profiles[current_name] = ProfileSpec(
                description=current_description,
                focus=current_focus,
            )
        current_name = None
        current_description = ""
        current_focus = []

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("active_profile:"):
            active_profile = stripped.split(":", 1)[1].strip()
            continue
        if stripped == "profiles:":
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    ") and stripped.endswith(":"):
            flush_current()
            current_name = stripped[:-1]
            in_focus = False
            continue
        if current_name is None:
            continue
        if stripped.startswith("description:"):
            current_description = stripped.split(":", 1)[1].strip()
            in_focus = False
        elif stripped == "focus:":
            in_focus = True
        elif in_focus and stripped.startswith("- "):
            current_focus.append(stripped[2:].strip())
    flush_current()
    return ProjectProfile(active_profile=active_profile, profiles=profiles)
