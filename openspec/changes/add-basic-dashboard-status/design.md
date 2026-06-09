# Design: add-basic-dashboard-status

## Architecture

- `collect_dashboard_data(root)` remains the single data assembly boundary.
- `src/agentos/ui/layout.py` owns render models and Rich/plain render output.
- `agentos dashboard` remains a thin CLI command that loads the theme, collects
  data, and renders Rich or plain output.

## Interfaces

- CLI:
  - `agentos dashboard`
  - `agentos dashboard --plain`
- Data additions:
  - `DashboardData.memory_count`
  - `DashboardData.registered_skills`
  - `DashboardData.recent_policy_violations`

## Safety

- Dashboard is read-only for memory, traces, SDD, and skill display.
- Skill summary discovery reads `SKILL.md` metadata but does not write the registry.
- Policy violations come from trace events, which already redact sensitive values.
- Commands are not executed by the dashboard.
