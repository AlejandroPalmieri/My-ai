from agentos.policies.checker import PolicyChecker, create_default_policies


def test_policy_checker_flags_sensitive_paths_and_destructive_commands(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    path_result = checker.check_path(".env")
    command_result = checker.check_command("rm -rf project")

    assert not path_result.allowed
    assert "sensitive" in path_result.reason
    assert not command_result.allowed
    assert "destructive" in command_result.reason


def test_policy_checker_allows_unlisted_path_and_command(tmp_path):
    create_default_policies(tmp_path)
    checker = PolicyChecker.from_directory(tmp_path / "policies")

    assert checker.check_path("README.md").allowed
    assert checker.check_command("pytest").allowed
