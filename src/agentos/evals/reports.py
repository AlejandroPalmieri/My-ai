from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentos.logging.traces import REDACTED, SENSITIVE_TERMS

RESULTS_DIR = Path(".agentos") / "evals" / "results"
REPORT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
EVAL_SENSITIVE_TERMS = {*SENSITIVE_TERMS, "api-key", "credential", "password", "secret"}
EVAL_SENSITIVE_KEY_TERMS = {
    *EVAL_SENSITIVE_TERMS,
    "authorization",
    "database-url",
    "database_url",
}
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(api[_-]?key|token|secret|credential|password|database[_-]?url)\b"
    r"\s*([:=])\s*[^\s,;|]+",
    re.IGNORECASE,
)
SECRET_TOKEN_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]+")
AUTHORIZATION_BEARER_PATTERN = re.compile(
    r"\b(Authorization\s*:\s*Bearer\s+)[^\s,;|]+",
    re.IGNORECASE,
)
BEARER_TOKEN_PATTERN = re.compile(r"\b(Bearer\s+)[A-Za-z0-9._~+/-]+=*", re.IGNORECASE)
JWT_TOKEN_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)


def report_paths(root: Path, report_id: str) -> tuple[Path, Path]:
    validate_report_id(report_id)
    project_root = _project_root(root)
    results_dir = _safe_results_dir(project_root)
    json_path = results_dir / f"{report_id}.json"
    markdown_path = results_dir / f"{report_id}.md"
    _ensure_contained(project_root, json_path, "Invalid eval report path.")
    _ensure_contained(project_root, markdown_path, "Invalid eval report path.")
    return json_path, markdown_path


def write_report(root: Path, report: Any) -> tuple[Path, Path]:
    json_path, markdown_path = report_paths(root, report.id)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = report_paths(root, report.id)
    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown_report(report: Any) -> str:
    summary = report.summary
    lines = [
        f"# AgentOS Eval Report `{report.id}`",
        "",
        f"- Category: `{report.category}`",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Skipped: {summary['skipped']}",
        f"- Duration: {report.duration_ms}ms",
        f"- AgentOS version: {report.agentos_version}",
        "",
        "## Environment",
        "",
    ]
    for key, value in report.environment.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Category | Case | Status | Duration | Detail |",
            "|---|---|---:|---:|---|",
        ]
    )
    for case in report.cases:
        detail = safe_report_text(case.detail).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{case.category}` | `{case.name}` | {case.status} | "
            f"{case.duration_ms}ms | {detail} |"
        )
    if report.failures:
        lines.extend(["", "## Failures", ""])
        for failure in report.failures:
            lines.append(f"- `{failure['name']}`: {safe_report_text(failure['detail'])}")
    return "\n".join(lines) + "\n"


def load_report(root: Path, report_id: str) -> dict[str, Any]:
    path = report_json_path(root, report_id)
    if not path.exists():
        raise FileNotFoundError(f"Eval report not found: {report_id}")
    return redact_report_payload(json.loads(path.read_text(encoding="utf-8")))


def latest_report(root: Path) -> dict[str, Any]:
    path = latest_report_path(root)
    if path is None:
        raise FileNotFoundError("No eval reports found.")
    return redact_report_payload(json.loads(path.read_text(encoding="utf-8")))


def latest_report_path(root: Path) -> Path | None:
    project_root = _project_root(root)
    results_dir = _safe_results_dir(project_root)
    if not results_dir.exists():
        return None
    reports = []
    for path in results_dir.glob("*.json"):
        _ensure_contained(project_root, path, "Invalid eval report path.")
        reports.append(path)
    reports = sorted(reports, key=lambda path: path.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def report_json_path(root: Path, report_id: str) -> Path:
    validate_report_id(report_id)
    project_root = _project_root(root)
    results_dir = _safe_results_dir(project_root)
    path = results_dir / f"{report_id}.json"
    _ensure_contained(project_root, path, "Invalid eval report id.")
    return path


def _project_root(root: Path) -> Path:
    return root.resolve(strict=False)


def _safe_results_dir(project_root: Path) -> Path:
    results_dir = project_root / RESULTS_DIR
    if results_dir.is_symlink():
        raise ValueError("Invalid eval results directory.")
    _ensure_contained(project_root, results_dir, "Invalid eval results directory.")
    if results_dir.exists() and not results_dir.is_dir():
        raise ValueError("Invalid eval results directory.")
    return results_dir


def _ensure_contained(project_root: Path, path: Path, message: str) -> None:
    if not path.resolve(strict=False).is_relative_to(project_root):
        raise ValueError(message)


def validate_report_id(report_id: str) -> None:
    if not REPORT_ID_PATTERN.fullmatch(report_id):
        raise ValueError("Invalid eval report id.")


def redact_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _redact_value(payload)


def safe_report_text(value: object) -> str:
    return str(_redact_value(str(value)))


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _redact_by_key(str(key), item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_by_key(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return REDACTED
    return _redact_value(value)


def _redact_text(value: str) -> str:
    redacted = SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", value
    )
    redacted = AUTHORIZATION_BEARER_PATTERN.sub(
        lambda match: f"{match.group(1)}{REDACTED}", redacted
    )
    redacted = BEARER_TOKEN_PATTERN.sub(lambda match: f"{match.group(1)}{REDACTED}", redacted)
    redacted = JWT_TOKEN_PATTERN.sub(REDACTED, redacted)
    redacted = SECRET_TOKEN_PATTERN.sub(REDACTED, redacted)
    return REDACTED if _is_sensitive_text(redacted) else redacted


def _is_sensitive_key(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return any(term in normalized for term in EVAL_SENSITIVE_KEY_TERMS)


def _is_sensitive_text(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return any(term in normalized for term in EVAL_SENSITIVE_TERMS)
