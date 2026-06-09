from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentos.refiner.analyzer import RefinerAnalysis


@dataclass(frozen=True)
class Proposal:
    path: Path
    title: str
    finding_count: int


class ProposalWriter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.proposals_dir = root / ".agentos" / "refiner" / "proposals"

    def write(self, analysis: RefinerAnalysis) -> Proposal:
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        slug = "no-findings" if not analysis.findings else analysis.findings[0].finding_type
        path = self.proposals_dir / f"{analysis.generated_at[:10]}-{slug}.md"
        title = "AgentOS Refiner Proposal"
        path.write_text(self._render(title, analysis), encoding="utf-8")
        return Proposal(path=path, title=title, finding_count=len(analysis.findings))

    def list(self) -> list[Path]:
        if not self.proposals_dir.exists():
            return []
        return sorted(self.proposals_dir.glob("*.md"))

    def _render(self, title: str, analysis: RefinerAnalysis) -> str:
        lines = [
            f"# {title}",
            "",
            "Status: proposed",
            "Human approval required before any implementation.",
            "",
            "Safety: this proposal does not edit AGENTS.md, skills, policies, or source code.",
            "It only records suggested changes for a future human-reviewed phase.",
            "",
            "## Trace Analysis",
            "",
            f"- Generated at: {analysis.generated_at}",
            f"- Events scanned: {analysis.events_scanned}",
            f"- Findings: {len(analysis.findings)}",
            "",
            "## Findings",
            "",
        ]
        if not analysis.findings:
            lines.append("No repeated failures, policy violations, or failed searches were found.")
        for finding in analysis.findings:
            lines.extend(
                [
                    f"### {finding.finding_type}",
                    "",
                    f"- Severity: {finding.severity}",
                    f"- Subject: {finding.subject}",
                    f"- Count: {finding.count}",
                    f"- Detail: {finding.detail}",
                    f"- Recommendation: {finding.recommendation}",
                    "",
                ]
            )
        lines.extend(
            [
                "## Next Step",
                "",
                "Review this proposal manually, decide whether a code or documentation change is "
                "warranted, and create a normal SDD change before implementation.",
                "",
            ]
        )
        return "\n".join(lines)
