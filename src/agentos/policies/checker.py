from __future__ import annotations

import fnmatch
import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

SENSITIVE_PATHS = [
    ".env",
    ".env.local",
    "*.pem",
    "*.key",
    ".ssh/",
    "credentials/",
    "secrets/",
    "id_rsa",
    "id_ed25519",
    "private_key",
    "token",
    "api_key",
    "banking",
    "medical_records",
]
DESTRUCTIVE_COMMANDS = [
    "rm -rf",
    "del /s /q",
    "Remove-Item -Recurse -Force",
    "git push --force",
    "git reset --hard",
    "DROP DATABASE",
    "docker system prune",
    "format",
    "diskpart",
    "database drop",
    "database reset",
    "chmod -R",
    "chown -R",
    "rotate credentials",
]
APPROVAL_COMMANDS = [
    "git push",
    "pip install",
    "python -m pip install",
    "docker run",
]


class PolicySeverity(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class PolicyRule(BaseModel):
    rule_type: str
    pattern: str
    severity: PolicySeverity
    reason: str
    source: str


class PolicyResult(BaseModel):
    severity: PolicySeverity
    reason: str
    matched_rule: str | None = None
    rule_type: str | None = None

    @property
    def allowed(self) -> bool:
        return self.severity != PolicySeverity.BLOCK


class PolicyChecker(BaseModel):
    sensitive_paths: list[str]
    destructive_commands: list[str]
    approval_commands: list[str]

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
            approval_commands=_read_yaml_list(
                policies_dir / "approval_rules.yaml",
                "approval_commands",
            ),
        )

    def check_path(self, path: str) -> PolicyResult:
        matched_rule = _match_path_rule(path, self.sensitive_paths)
        if matched_rule is not None:
            return PolicyResult(
                severity=PolicySeverity.BLOCK,
                reason=f"Blocked sensitive path: {path}",
                matched_rule=matched_rule,
                rule_type="sensitive_path",
            )
        return PolicyResult(
            severity=PolicySeverity.ALLOW,
            reason=f"Allowed path: {path}",
            rule_type="path",
        )

    def check_command(self, command: str) -> PolicyResult:
        destructive_rule = _match_command_rule(command, self.destructive_commands)
        if destructive_rule is not None:
            return PolicyResult(
                severity=PolicySeverity.BLOCK,
                reason=f"Blocked destructive command: {command}",
                matched_rule=destructive_rule,
                rule_type="destructive_command",
            )

        approval_rule = _match_command_rule(command, self.approval_commands)
        if approval_rule is not None:
            return PolicyResult(
                severity=PolicySeverity.WARN,
                reason=f"Command requires explicit approval: {command}",
                matched_rule=approval_rule,
                rule_type="approval_command",
            )

        return PolicyResult(
            severity=PolicySeverity.ALLOW,
            reason=f"Allowed command: {command}",
            rule_type="command",
        )

    def list_rules(self) -> list[PolicyRule]:
        rules = [
            PolicyRule(
                rule_type="sensitive_path",
                pattern=pattern,
                severity=PolicySeverity.BLOCK,
                reason="Sensitive paths are blocked.",
                source="sensitive_paths.yaml",
            )
            for pattern in self.sensitive_paths
        ]
        rules.extend(
            PolicyRule(
                rule_type="destructive_command",
                pattern=pattern,
                severity=PolicySeverity.BLOCK,
                reason="Destructive commands are blocked.",
                source="destructive_commands.yaml",
            )
            for pattern in self.destructive_commands
        )
        rules.extend(
            PolicyRule(
                rule_type="approval_command",
                pattern=pattern,
                severity=PolicySeverity.WARN,
                reason="Approval rules return warn and require explicit user review.",
                source="approval_rules.yaml",
            )
            for pattern in self.approval_commands
        )
        return rules

    def explain(self) -> str:
        return (
            "Sensitive paths are blocked before access. "
            "Destructive commands are blocked before execution. "
            "Approval rules return warn and require explicit user review. "
            "Checks are local text analysis only; commands are never executed."
        )


def create_default_policies(root: Path) -> None:
    policies_dir = root / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml_list(policies_dir / "sensitive_paths.yaml", "sensitive_paths", SENSITIVE_PATHS)
    _write_yaml_list(
        policies_dir / "destructive_commands.yaml",
        "destructive_commands",
        DESTRUCTIVE_COMMANDS,
    )
    _write_yaml_list(
        policies_dir / "approval_rules.yaml",
        "approval_commands",
        APPROVAL_COMMANDS,
    )


def _match_path_rule(path: str, patterns: list[str]) -> str | None:
    normalized = _normalize_path(path)
    directory_patterns = [pattern for pattern in patterns if pattern.endswith(("/", "\\"))]
    other_patterns = [pattern for pattern in patterns if pattern not in directory_patterns]
    for pattern in directory_patterns + other_patterns:
        if _path_matches_pattern(normalized, pattern):
            return pattern
    return None


def _path_matches_pattern(normalized_path: str, pattern: str) -> bool:
    candidate = _normalize_path(pattern)
    path_parts = [part for part in normalized_path.split("/") if part]
    if candidate.endswith("/"):
        directory_name = candidate.strip("/")
        return directory_name in path_parts or f"/{directory_name}/" in f"/{normalized_path}"
    if "*" in candidate:
        return fnmatch.fnmatch(normalized_path, candidate) or any(
            fnmatch.fnmatch(part, candidate) for part in path_parts
        )
    return normalized_path == candidate or candidate in path_parts or candidate in normalized_path


def _match_command_rule(command: str, patterns: list[str]) -> str | None:
    normalized_command = _normalize_command(command)
    command_tokens = _command_tokens(normalized_command)
    for pattern in patterns:
        normalized_pattern = _normalize_command(pattern)
        if normalized_pattern.startswith("remove-item "):
            if _powershell_remove_item_matches(command_tokens, normalized_pattern):
                return pattern
        elif _command_pattern_matches(normalized_command, command_tokens, normalized_pattern):
            return pattern
    return None


def _command_pattern_matches(
    normalized_command: str,
    command_tokens: list[str],
    normalized_pattern: str,
) -> bool:
    pattern_tokens = _command_tokens(normalized_pattern)
    if len(pattern_tokens) == 1:
        return pattern_tokens[0] in command_tokens
    return normalized_pattern in normalized_command


def _powershell_remove_item_matches(
    command_tokens: list[str],
    normalized_pattern: str,
) -> bool:
    pattern_tokens = _command_tokens(normalized_pattern)
    return all(token in command_tokens for token in pattern_tokens)


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lower().strip()


def _normalize_command(command: str) -> str:
    without_quotes = command.replace('"', " ").replace("'", " ")
    without_punctuation = re.sub(r"[;,]+", " ", without_quotes)
    return " ".join(without_punctuation.lower().split())


def _command_tokens(command: str) -> list[str]:
    return command.split()


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
