from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from agentos.evals.runner import EvalRunner
from agentos.services.container import create_service_container
from agentos.ui.dashboard import collect_dashboard_data, render_dashboard
from agentos.ui.layout import DashboardData
from agentos.ui.theme import Theme

PANES = ["overview", "memory", "sdd", "skills", "policies", "traces", "runtime"]
PANE_KEYS = {
    "m": "memory",
    "s": "sdd",
    "p": "policies",
    "t": "traces",
    "o": "overview",
}


@dataclass(frozen=True)
class DashboardActionResult:
    message: str
    should_exit: bool = False


class DashboardController:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.focus = "overview"
        self.data = collect_dashboard_data(root)
        self.last_message = "Interactive dashboard ready"

    def handle_key(self, key: str) -> DashboardActionResult:
        normalized = key.lower().strip()
        if normalized in {"q", "esc"}:
            return self._message("Dashboard closed", should_exit=True)
        if normalized in {"tab", "\t", "n"}:
            return self._focus_next()
        if normalized in PANE_KEYS:
            self.focus = PANE_KEYS[normalized]
            return self._message(f"Focused {self.focus.upper()}")
        if normalized == "r":
            self.refresh()
            return self._message("Dashboard refreshed")
        if normalized == "b":
            backup = create_service_container(self.root).backups.create()
            self.refresh()
            return self._message(f"Backup created {backup.id}")
        if normalized == "k":
            return self.scan_skills()
        if normalized == "e":
            report = EvalRunner(self.root).run()
            self.refresh()
            status = "passed" if report.passed else "failed"
            return self._message(f"Eval run {status}: {report.result_path}")
        if normalized == "u":
            return self._message(
                "Policy traces cannot reveal sensitive redacted values; "
                "inspect policy rules instead."
            )
        if normalized == "h":
            return self._message(
                "Keys: tab/n focus, r refresh, b backup, e eval, k scan skills, "
                "m/s/p/t/o panes, q quit"
            )
        return self._message(f"Unknown key: {key}")

    def scan_skills(self) -> DashboardActionResult:
        registry = create_service_container(self.root).skills.scan()
        self.refresh()
        return self._message(f"Scanned {len(registry.skills)} skills")

    def refresh(self) -> DashboardData:
        self.data = collect_dashboard_data(self.root)
        return self.data

    def render(self, theme: Theme, *, compact: bool = False, plain: bool = False):
        dashboard = render_dashboard(self.data, theme, compact=compact, plain=plain)
        if plain:
            return (
                "Interactive dashboard\n"
                f"Focused pane: {self.focus}\n"
                f"Status: {self.last_message}\n"
                f"{dashboard}\n"
                "[tab] next pane | [r] refresh | [b] backup | [e] eval | "
                "[k] scan skills | [m/s/p/t/o] focus | [q] quit"
            )
        return Panel.fit(
            dashboard,
            title=f"Interactive dashboard | focus: {self.focus} | {self.last_message}",
            subtitle="[tab] next pane | [r] refresh | [b] backup | [e] eval | [q] quit",
        )

    def _focus_next(self) -> DashboardActionResult:
        current = PANES.index(self.focus)
        self.focus = PANES[(current + 1) % len(PANES)]
        return self._message(f"Focused {self.focus.upper()}")

    def _message(self, message: str, *, should_exit: bool = False) -> DashboardActionResult:
        self.last_message = message
        return DashboardActionResult(message=message, should_exit=should_exit)


def run_interactive_dashboard(
    root: Path,
    console: Console,
    theme: Theme,
    *,
    plain: bool = False,
    once: bool = False,
) -> None:
    controller = DashboardController(root)
    compact = console.width < 100
    rendered = controller.render(theme, compact=compact, plain=plain)
    console.print(rendered, markup=not isinstance(rendered, str))
    if once:
        return
    while True:
        key = _read_key()
        if key.lower() == "k":
            result = controller.scan_skills()
        else:
            result = controller.handle_key(key)
        if result.should_exit:
            console.print(result.message)
            return
        if not plain:
            console.clear()
        rendered = controller.render(theme, compact=compact, plain=plain)
        console.print(rendered, markup=not isinstance(rendered, str))


def _read_key() -> str:
    if os.name == "nt":
        import msvcrt

        char = msvcrt.getwch()
        if char in {"\x00", "\xe0"}:
            msvcrt.getwch()
            return ""
        return "tab" if char == "\t" else char
    char = sys.stdin.read(1)
    return "tab" if char == "\t" else char
