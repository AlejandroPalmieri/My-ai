from pathlib import Path

from pydantic import BaseModel

SDD_FILES = ("proposal.md", "design.md", "tasks.md", "verify-report.md", "sync-report.md")


class SDDChange(BaseModel):
    name: str
    path: Path
    files: list[Path]


def create_change(root: Path, change_name: str) -> SDDChange:
    change_dir = root / "openspec" / "changes" / change_name
    change_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for filename in SDD_FILES:
        path = change_dir / filename
        if not path.exists():
            path.write_text(_template(filename, change_name), encoding="utf-8")
        files.append(path)
    return SDDChange(name=change_name, path=change_dir, files=files)


def _template(filename: str, change_name: str) -> str:
    title = filename.removesuffix(".md").replace("-", " ").title()
    return f"# {title}: {change_name}\n\nStatus: draft\n\n"
