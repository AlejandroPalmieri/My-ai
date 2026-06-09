from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.refiner.analyzer import TraceRefiner
from agentos.refiner.proposals import ProposalWriter


def test_refiner_detects_repeated_command_failures(tmp_path):
    logger = TraceLogger(tmp_path)
    logger.log_event(
        TraceEventType.COMMAND_FAILED,
        command="memory.search",
        status="failed",
        error="query failed",
    )
    logger.log_event(
        TraceEventType.COMMAND_FAILED,
        command="memory.search",
        status="failed",
        error="query failed again",
    )

    analysis = TraceRefiner(tmp_path).analyze()

    assert analysis.findings
    finding = analysis.finding_by_type("repeated_command_failures")
    assert finding is not None
    assert finding.subject == "memory.search"
    assert finding.count == 2


def test_refiner_detects_policy_violations_and_failed_searches(tmp_path):
    logger = TraceLogger(tmp_path)
    logger.log_event(
        TraceEventType.POLICY_VIOLATION,
        command="policies.check",
        status="block",
        payload={"matched_rule": ".env", "reason": "Sensitive path"},
    )
    logger.log_event(
        TraceEventType.POLICY_VIOLATION,
        command="policies.check",
        status="block",
        payload={"matched_rule": ".env", "reason": "Sensitive path"},
    )
    logger.log_event(
        TraceEventType.MEMORY_SEARCHED,
        command="memory.search",
        status="ok",
        payload={"query": "missing topic", "result_count": 0},
    )

    analysis = TraceRefiner(tmp_path).analyze()

    assert analysis.finding_by_type("frequent_policy_violations") is not None
    assert analysis.finding_by_type("failed_searches") is not None


def test_proposal_writer_creates_markdown_without_auto_edits(tmp_path):
    logger = TraceLogger(tmp_path)
    logger.log_event(
        TraceEventType.COMMAND_FAILED,
        command="skills.validate",
        status="failed",
        error="missing description",
    )
    logger.log_event(
        TraceEventType.COMMAND_FAILED,
        command="skills.validate",
        status="failed",
        error="missing description",
    )
    analysis = TraceRefiner(tmp_path).analyze()

    proposal = ProposalWriter(tmp_path).write(analysis)

    assert proposal.path.parent == tmp_path / ".agentos" / "refiner" / "proposals"
    assert proposal.path.exists()
    content = proposal.path.read_text(encoding="utf-8")
    assert "Human approval required" in content
    assert "does not edit AGENTS.md, skills, policies, or source code" in content
    assert "skills.validate" in content
