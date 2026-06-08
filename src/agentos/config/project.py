from pathlib import Path

from pydantic import BaseModel

from agentos.config.profiles import create_default_profile
from agentos.policies.checker import create_default_policies


class ProjectInitResult(BaseModel):
    root: Path
    agentos_dir: Path


def init_project(root: Path) -> ProjectInitResult:
    root = root.resolve()
    agentos_dir = root / ".agentos"
    agentos_dir.mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    (root / "openspec" / "specs").mkdir(parents=True, exist_ok=True)
    (root / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    create_default_policies(root)
    create_default_profile(root)
    return ProjectInitResult(root=root, agentos_dir=agentos_dir)
