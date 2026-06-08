from agentos.config.profiles import ProjectProfile, create_default_profile
from agentos.policies.checker import PolicyChecker, PolicySeverity, create_default_policies
from agentos.services.local import LocalPolicyService


def test_policy_checker_flags_sensitive_paths_and_destructive_commands(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    path_result = checker.check_path(".env")
    command_result = checker.check_command("rm -rf project")

    assert not path_result.allowed
    assert path_result.severity == PolicySeverity.BLOCK
    assert "sensitive" in path_result.reason
    assert path_result.matched_rule == ".env"
    assert not command_result.allowed
    assert command_result.severity == PolicySeverity.BLOCK
    assert "destructive" in command_result.reason
    assert command_result.matched_rule == "rm -rf"


def test_policy_checker_allows_unlisted_path_and_command(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    assert checker.check_path("README.md").allowed
    assert checker.check_command("pytest").allowed
    assert checker.check_command("pytest").severity == PolicySeverity.ALLOW


def test_policy_checker_flags_sensitive_path_patterns(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    results = [
        checker.check_path("config/prod.pem"),
        checker.check_path("C:/Users/example/.ssh/id_ed25519"),
        checker.check_path("credentials/service-token.txt"),
        checker.check_path("notes/medical_records/visit.md"),
        checker.check_path("banking/export.csv"),
    ]

    assert all(result.severity == PolicySeverity.BLOCK for result in results)
    assert [result.matched_rule for result in results] == [
        "*.pem",
        ".ssh/",
        "credentials/",
        "medical_records",
        "banking",
    ]


def test_policy_checker_flags_dangerous_commands_without_executing_them(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    results = [
        checker.check_command("git reset --hard HEAD"),
        checker.check_command("git push --force origin main"),
        checker.check_command("DROP DATABASE production"),
        checker.check_command("docker system prune -af"),
        checker.check_command("format C:"),
        checker.check_command("diskpart /s wipe.txt"),
    ]

    assert all(result.severity == PolicySeverity.BLOCK for result in results)
    assert [result.matched_rule for result in results] == [
        "git reset --hard",
        "git push --force",
        "DROP DATABASE",
        "docker system prune",
        "format",
        "diskpart",
    ]


def test_policy_checker_flags_powershell_remove_item(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    result = checker.check_command("Remove-Item -LiteralPath .\\build -Recurse -Force")

    assert result.severity == PolicySeverity.BLOCK
    assert result.matched_rule == "Remove-Item -Recurse -Force"


def test_policy_checker_warns_for_approval_rules(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    result = checker.check_command("git push origin main")

    assert result.allowed
    assert result.severity == PolicySeverity.WARN
    assert result.matched_rule == "git push"


def test_policy_checker_lists_and_explains_rules(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    listing = checker.list_rules()
    explanation = checker.explain()

    assert any(
        rule.pattern == "*.key" and rule.severity == PolicySeverity.BLOCK for rule in listing
    )
    assert "Sensitive paths are blocked" in explanation
    assert "Approval rules return warn" in explanation


def test_profile_blocked_paths_extend_local_policy_service(tmp_path):
    create_default_policies(tmp_path)
    profile_path = create_default_profile(tmp_path)
    profile = ProjectProfile.read(profile_path)
    profile.active_profile = "godot"
    profile.profiles["godot"].blocked_paths.append("exports/private/")
    profile.write(profile_path)

    result = LocalPolicyService(tmp_path).check_path("exports/private/build.zip")

    assert result.severity == PolicySeverity.BLOCK
    assert result.matched_rule == "exports/private/"
