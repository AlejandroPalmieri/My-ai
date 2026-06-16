from __future__ import annotations

from pathlib import Path

SENSITIVE_MARKERS = (
    ".env",
    ".ssh",
    "credentials",
    "secrets",
    "id_rsa",
    "id_ed25519",
    "token",
    "api_key",
)


def excerpt(text: str, limit: int = 360) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def is_sensitive_text(*values: str | None) -> bool:
    joined = " ".join(value or "" for value in values).lower().replace("\\", "/")
    return any(marker in joined for marker in SENSITIVE_MARKERS)


def is_hidden_path(path: str) -> bool:
    return any(part.startswith(".") for part in Path(path).parts)


def memory_label(memory_id: str) -> str:
    return f"memory:{memory_id}"


def brain_label(document_id: str, chunk_id: str) -> str:
    return f"brain:{document_id}#{chunk_id}"
