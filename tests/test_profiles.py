from agentos.config.profiles import (
    DEFAULT_PROFILES,
    ProjectProfile,
    create_default_profile,
    load_profile,
    set_active_profile,
    validate_profile,
)


def test_create_and_load_default_profile(tmp_path):
    profile_path = create_default_profile(tmp_path)
    profile = load_profile(profile_path)

    assert profile_path == tmp_path / ".agentos" / "profile.yaml"
    assert profile.active_profile == "default"
    assert set(profile.profiles) == {
        "default",
        "godot",
        "bioinformatics",
        "usmle",
        "neocircuit",
        "data-science",
    }
    assert profile.active.default_project == "default"
    assert profile.active.memory_project == "default"
    assert profile.active.sdd_required_for
    assert isinstance(profile.active.blocked_paths, list)
    assert DEFAULT_PROFILES["godot"].description


def test_project_profile_round_trips_yaml(tmp_path):
    path = tmp_path / "profile.yaml"
    original = ProjectProfile(
        active_profile="data-science",
        profiles={"data-science": DEFAULT_PROFILES["data-science"]},
    )

    original.write(path)
    loaded = ProjectProfile.read(path)

    assert loaded.active_profile == "data-science"
    assert loaded.active.name == "data-science"
    assert (
        loaded.profiles["data-science"].description
        == DEFAULT_PROFILES["data-science"].description
    )


def test_set_active_profile_updates_profile_file(tmp_path):
    path = create_default_profile(tmp_path)

    profile = set_active_profile(path, "usmle")

    assert profile.active_profile == "usmle"
    assert ProjectProfile.read(path).active_profile == "usmle"


def test_validate_profile_warns_for_unknown_skills(tmp_path):
    path = create_default_profile(tmp_path)
    profile = ProjectProfile.read(path)
    profile.profiles["default"].preferred_skills.append("missing-skill")
    profile.write(path)

    validation = validate_profile(path, known_skills={"sqlite-memory"})

    assert validation.valid is True
    assert any("missing-skill" in warning for warning in validation.warnings)


def test_active_profile_blocked_paths_extend_policy_checks(tmp_path):
    path = create_default_profile(tmp_path)
    profile = ProjectProfile.read(path)
    profile.active_profile = "godot"
    profile.profiles["godot"].blocked_paths.append("exports/private/")
    profile.write(path)

    assert "exports/private/" in ProjectProfile.read(path).active.blocked_paths
