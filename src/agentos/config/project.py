from pathlib import Path

from pydantic import BaseModel

from agentos.config.profiles import create_default_profile
from agentos.config.settings import create_default_config
from agentos.models.config import create_default_model_config
from agentos.models.routing import create_default_routing_config
from agentos.policies.checker import create_default_policies


class ProjectInitResult(BaseModel):
    root: Path
    agentos_dir: Path


def init_project(root: Path) -> ProjectInitResult:
    root = root.resolve()
    agentos_dir = root / ".agentos"
    agentos_dir.mkdir(parents=True, exist_ok=True)
    (agentos_dir / "agents").mkdir(parents=True, exist_ok=True)
    (agentos_dir / "brain").mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    (root / "openspec" / "specs").mkdir(parents=True, exist_ok=True)
    (root / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    create_default_policies(root)
    create_default_profile(root)
    create_default_config(root)
    create_default_model_config(root)
    create_default_routing_config(root)
    return ProjectInitResult(root=root, agentos_dir=agentos_dir)
