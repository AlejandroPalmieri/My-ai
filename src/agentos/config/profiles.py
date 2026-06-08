from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ProfileSpec(BaseModel):
    name: str
    description: str
    default_project: str
    memory_project: str
    preferred_skills: list[str]
    sdd_required_for: list[str]
    blocked_paths: list[str]
    test_commands: list[str]
    notes: list[str]


class ProfileValidation(BaseModel):
    valid: bool
    warnings: list[str]
    errors: list[str]


class ProjectProfile(BaseModel):
    active_profile: str
    profiles: dict[str, ProfileSpec]

    @property
    def active(self) -> ProfileSpec:
        return self.profiles[self.active_profile]

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"active_profile: {self.active_profile}", "profiles:"]
        for name, profile in self.profiles.items():
            lines.append(f"  {name}:")
            lines.append(f"    name: {profile.name}")
            lines.append(f"    description: {profile.description}")
            lines.append(f"    default_project: {profile.default_project}")
            lines.append(f"    memory_project: {profile.memory_project}")
            _write_list(lines, "preferred_skills", profile.preferred_skills)
            _write_list(lines, "sdd_required_for", profile.sdd_required_for)
            _write_list(lines, "blocked_paths", profile.blocked_paths)
            _write_list(lines, "test_commands", profile.test_commands)
            _write_list(lines, "notes", profile.notes)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> ProjectProfile:
        return _parse_profile(path.read_text(encoding="utf-8"))


DEFAULT_PROFILES = {
    "default": ProfileSpec(
        name="default",
        description="General local AgentOS work without a specialized domain mode.",
        default_project="default",
        memory_project="default",
        preferred_skills=["safety-review", "sdd-workflow"],
        sdd_required_for=["architecture", "security", "cli", "memory", "policies"],
        blocked_paths=[".env", "secrets/", "credentials/"],
        test_commands=["pytest"],
        notes=["Use conservative local-first defaults."],
    ),
    "godot": ProfileSpec(
        name="godot",
        description="Game development workflows centered on Godot projects.",
        default_project="godot",
        memory_project="godot",
        preferred_skills=["safety-review", "sdd-workflow"],
        sdd_required_for=["gameplay systems", "editor plugins", "export tooling"],
        blocked_paths=["exports/private/", "addons/**/.env"],
        test_commands=["pytest"],
        notes=["Track gameplay decisions, asset pipeline notes, and playtest findings."],
    ),
    "bioinformatics": ProfileSpec(
        name="bioinformatics",
        description="Local analysis workflows for biological datasets and pipelines.",
        default_project="bioinformatics",
        memory_project="bioinformatics",
        preferred_skills=["safety-review", "sdd-workflow"],
        sdd_required_for=["pipelines", "data transforms", "reproducibility"],
        blocked_paths=["patient_data/", "raw_genomes/private/"],
        test_commands=["pytest"],
        notes=["Record provenance, parameters, and reproducibility decisions."],
    ),
    "usmle": ProfileSpec(
        name="usmle",
        description="Study and retrieval workflows for USMLE preparation.",
        default_project="usmle",
        memory_project="usmle",
        preferred_skills=["safety-review"],
        sdd_required_for=["study workflows", "retrieval changes"],
        blocked_paths=["medical_records/", "patient_notes/"],
        test_commands=["pytest"],
        notes=["Keep study notes separate from private medical records."],
    ),
    "neocircuit": ProfileSpec(
        name="neocircuit",
        description="Neocircuit research and knowledge synthesis workspace.",
        default_project="neocircuit",
        memory_project="neocircuit",
        preferred_skills=["safety-review", "sdd-workflow"],
        sdd_required_for=["hypotheses", "entity models", "synthesis workflows"],
        blocked_paths=["private_research/", "credentials/"],
        test_commands=["pytest"],
        notes=["Capture hypotheses, entity links, and synthesis decisions."],
    ),
    "data-science": ProfileSpec(
        name="data-science",
        description="Data science project workflows from exploration to reporting.",
        default_project="data-science",
        memory_project="data-science",
        preferred_skills=["safety-review", "sdd-workflow"],
        sdd_required_for=["datasets", "modeling", "reports"],
        blocked_paths=["raw/private/", "credentials/", "secrets/"],
        test_commands=["pytest"],
        notes=["Record dataset assumptions, experiments, and evaluation results."],
    ),
}


def create_default_profile(root: Path) -> Path:
    path = root / ".agentos" / "profile.yaml"
    if not path.exists():
        ProjectProfile(active_profile="default", profiles=DEFAULT_PROFILES).write(path)
    return path


def load_profile(path: Path) -> ProjectProfile:
    return ProjectProfile.read(path)


def load_project_profile(root: Path) -> ProjectProfile:
    return load_profile(create_default_profile(root))


def set_active_profile(path: Path, profile_name: str) -> ProjectProfile:
    profile = ProjectProfile.read(path)
    if profile_name not in profile.profiles:
        raise KeyError(f"Unknown profile: {profile_name}")
    profile.active_profile = profile_name
    profile.write(path)
    return profile


def validate_profile(path: Path, known_skills: set[str] | None = None) -> ProfileValidation:
    errors = []
    warnings = []
    profile = ProjectProfile.read(path)
    if profile.active_profile not in profile.profiles:
        errors.append(f"Active profile not found: {profile.active_profile}")
    known = known_skills if known_skills is not None else set()
    for name, spec in profile.profiles.items():
        if spec.name != name:
            errors.append(f"Profile key/name mismatch: {name} != {spec.name}")
        for skill in spec.preferred_skills:
            if known_skills is not None and skill not in known:
                warnings.append(f"Profile {name} references unknown skill: {skill}")
    return ProfileValidation(valid=not errors, warnings=warnings, errors=errors)


def _write_list(lines: list[str], key: str, values: list[str]) -> None:
    lines.append(f"    {key}:")
    for item in values:
        lines.append(f"      - {item}")


def _parse_profile(content: str) -> ProjectProfile:
    active_profile = "default"
    profiles: dict[str, ProfileSpec] = {}
    current_name: str | None = None
    current_fields: dict[str, object] = {}
    current_list_key: str | None = None

    def flush_current() -> None:
        nonlocal current_name, current_fields, current_list_key
        if current_name is not None:
            fields = _profile_fields(current_name, current_fields)
            profiles[current_name] = ProfileSpec(**fields)
        current_name = None
        current_fields = {}
        current_list_key = None

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
            continue
        if current_name is None:
            continue
        if raw_line.startswith("    ") and not raw_line.startswith("      "):
            key, _, value = stripped.partition(":")
            if value.strip():
                current_fields[key] = value.strip()
                current_list_key = None
            else:
                current_fields[key] = []
                current_list_key = key
        elif current_list_key and stripped.startswith("- "):
            values = current_fields.setdefault(current_list_key, [])
            if isinstance(values, list):
                values.append(stripped[2:].strip())
    flush_current()
    return ProjectProfile(active_profile=active_profile, profiles=profiles)


def _profile_fields(name: str, fields: dict[str, object]) -> dict[str, object]:
    legacy_focus = _list_field(fields, "focus")
    return {
        "name": str(fields.get("name") or name),
        "description": str(fields.get("description") or ""),
        "default_project": str(fields.get("default_project") or name),
        "memory_project": str(
            fields.get("memory_project") or fields.get("default_project") or name
        ),
        "preferred_skills": _list_field(fields, "preferred_skills"),
        "sdd_required_for": _list_field(fields, "sdd_required_for") or legacy_focus,
        "blocked_paths": _list_field(fields, "blocked_paths"),
        "test_commands": _list_field(fields, "test_commands") or ["pytest"],
        "notes": _list_field(fields, "notes"),
    }


def _list_field(fields: dict[str, object], key: str) -> list[str]:
    value = fields.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [value]
    return []
