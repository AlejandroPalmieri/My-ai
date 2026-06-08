from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

SENSITIVE_PATHS = [
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519",
    "private_key",
    "credentials",
    "secrets",
]
DESTRUCTIVE_COMMANDS = [
    "rm -rf",
    "git push --force",
    "drop database",
    "database drop",
    "database reset",
    "chmod -R",
    "chown -R",
    "rotate credentials",
]


class PolicyResult(BaseModel):
    allowed: bool
    reason: str


class PolicyChecker(BaseModel):
    sensitive_paths: list[str]
    destructive_commands: list[str]

    @classmethod
    def from_directory(cls, policies_dir: Path) -> PolicyChecker:
        return cls(
            sensitive_paths=_read_yaml_list(
                policies_dir / "sensitive_paths.yaml",
                "sensitive_paths",
            ),
            destructive_commands=_read_yaml_list(
                policies_dir / "destructive_commands.yaml",
                "destructive_commands",
            ),
        )

    def check_path(self, path: str) -> PolicyResult:
        normalized = path.replace("\\", "/").lower()
        parts = {part for part in normalized.split("/") if part}
        for pattern in self.sensitive_paths:
            candidate = pattern.lower()
            if normalized == candidate or candidate in parts or candidate in normalized:
                return PolicyResult(allowed=False, reason=f"Blocked sensitive path: {path}")
        return PolicyResult(allowed=True, reason=f"Allowed path: {path}")

    def check_command(self, command: str) -> PolicyResult:
        normalized = " ".join(command.lower().split())
        for pattern in self.destructive_commands:
            if " ".join(pattern.lower().split()) in normalized:
                return PolicyResult(allowed=False, reason=f"Blocked destructive command: {command}")
        return PolicyResult(allowed=True, reason=f"Allowed command: {command}")


def create_default_policies(root: Path) -> None:
    policies_dir = root / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml_list(policies_dir / "sensitive_paths.yaml", "sensitive_paths", SENSITIVE_PATHS)
    _write_yaml_list(
        policies_dir / "destructive_commands.yaml",
        "destructive_commands",
        DESTRUCTIVE_COMMANDS,
    )


def _write_yaml_list(path: Path, key: str, values: list[str]) -> None:
    if path.exists():
        return
    body = key + ":\n" + "".join(f"  - {value}\n" for value in values)
    path.write_text(body, encoding="utf-8")


def _read_yaml_list(path: Path, key: str) -> list[str]:
    if not path.exists():
        return []
    values = []
    in_key = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == f"{key}:":
            in_key = True
            continue
        if in_key and stripped.startswith("- "):
            values.append(stripped[2:].strip().strip('"').strip("'"))
        elif in_key and stripped and not line.startswith((" ", "\t")):
            break
    return values
