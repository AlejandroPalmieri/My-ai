import subprocess
from pathlib import Path


def test_install_agentos_command_writes_idempotent_path_shim_and_removes_profile_block(tmp_path):
    script_path = Path("scripts/install-agentos-command.ps1")
    project_root = tmp_path / "agentos-personal"
    executable = project_root / ".venv" / "Scripts" / "agentos.exe"
    shim_directory = tmp_path / "bin"
    profile_path = tmp_path / "profile.ps1"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    profile_path.write_text(
        "\n".join(
            [
                "Write-Output 'keep this profile content'",
                "# >>> agentos-personal command >>>",
                "function agentos {",
                "    & 'old-agentos.exe' @args",
                "}",
                "# <<< agentos-personal command <<<",
            ]
        ),
        encoding="utf-8",
    )

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-ProjectRoot",
        str(project_root),
        "-ShimDirectory",
        str(shim_directory),
        "-ProfilePath",
        str(profile_path),
        "-SkipPackageInstall",
    ]

    first_result = subprocess.run(command, check=False, capture_output=True, text=True)
    second_result = subprocess.run(command, check=False, capture_output=True, text=True)

    assert first_result.returncode == 0, first_result.stderr
    assert second_result.returncode == 0, second_result.stderr
    shim_path = shim_directory / "agentos.cmd"
    shim_text = shim_path.read_text(encoding="utf-8")
    profile_text = profile_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    assert shim_text.count(str(executable)) == 1
    assert "%*" in shim_text
    assert "Write-Output 'keep this profile content'" in profile_text
    assert "function agentos" not in profile_text
    assert "AgentOS Personal command installed" in first_result.stdout
