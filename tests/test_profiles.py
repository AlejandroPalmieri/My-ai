from agentos.config.profiles import (
    DEFAULT_PROFILES,
    ProjectProfile,
    create_default_profile,
    load_profile,
)


def test_create_and_load_default_profile(tmp_path):
    profile_path = create_default_profile(tmp_path)
    profile = load_profile(profile_path)

    assert profile_path == tmp_path / ".agentos" / "profile.yaml"
    assert profile.active_profile == "godot"
    assert set(profile.profiles) == {
        "godot",
        "bioinformatics",
        "usmle",
        "neocircuit",
        "data-science",
    }
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
    assert (
        loaded.profiles["data-science"].description
        == DEFAULT_PROFILES["data-science"].description
    )
