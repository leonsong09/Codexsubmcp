from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from codexsubmcp.core.cleanup import build_candidate_suites
from codexsubmcp.core.config import DEFAULT_CONFIG, validate_config
from codexsubmcp.core.models import McpRecord, ProcessSuite
from codexsubmcp.core.stale_attached import (
    StaleAttachedBranch,
    build_attached_branches,
    find_stale_attached_branches,
    infer_record_tool_signature,
    infer_tool_signature,
)
from codexsubmcp.core.system_snapshot import SystemSnapshot


@dataclass(frozen=True)
class RunningMcpSummary:
    tool_signature: str
    instance_count: int
    live_codex_pid_count: int
    has_stale: bool


@dataclass(frozen=True)
class AnalysisSummary:
    configured_mcp_count: int
    running_mcp_instance_count: int
    open_subagent_count: int
    drift_missing_runtime_count: int
    drift_unconfigured_runtime_count: int
    live_suite_count: int
    orphan_suite_count: int
    stale_attached_branch_count: int


@dataclass(frozen=True)
class AnalysisResult:
    snapshot_id: str
    analyzed_at: datetime
    summary: AnalysisSummary
    running_mcps: tuple[RunningMcpSummary, ...]
    configured_not_running: tuple[str, ...]
    running_not_configured: tuple[str, ...]
    live_suites: tuple[ProcessSuite, ...]
    orphan_suites: tuple[ProcessSuite, ...]
    stale_attached_branches: tuple[StaleAttachedBranch, ...]


@dataclass(frozen=True)
class _RunningInstance:
    tool_signature: str
    live_codex_pid: int | None


def analyze_snapshot(
    snapshot: SystemSnapshot,
    *,
    config: dict[str, object] | None = None,
) -> AnalysisResult:
    merged_config = validate_config({**DEFAULT_CONFIG, **(config or {})})
    suites = build_candidate_suites(
        snapshot.processes,
        suite_window_seconds=int(merged_config["suite_window_seconds"]),
        config=merged_config,
    )
    live_suites = tuple(suite for suite in suites if suite.classification == "attached_to_live_codex")
    orphan_suites = tuple(suite for suite in suites if suite.classification == "orphaned_after_codex_exit")
    stale_attached_branches = tuple(
        stale
        for suite in live_suites
        for stale in find_stale_attached_branches(suite)
    )
    running_mcps = _build_running_mcp_summaries(live_suites=live_suites, orphan_suites=orphan_suites)
    configured_signatures = _configured_signatures(snapshot.configured_mcps)
    running_signatures = tuple(item.tool_signature for item in running_mcps)
    configured_not_running = tuple(sorted(configured_signatures - set(running_signatures)))
    running_not_configured = tuple(sorted(set(running_signatures) - configured_signatures))
    return AnalysisResult(
        snapshot_id=snapshot.snapshot_id,
        analyzed_at=datetime.now(),
        summary=AnalysisSummary(
            configured_mcp_count=len(snapshot.configured_mcps),
            running_mcp_instance_count=sum(item.instance_count for item in running_mcps),
            open_subagent_count=snapshot.codex.open_subagent_count,
            drift_missing_runtime_count=len(configured_not_running),
            drift_unconfigured_runtime_count=len(running_not_configured),
            live_suite_count=len(live_suites),
            orphan_suite_count=len(orphan_suites),
            stale_attached_branch_count=len(stale_attached_branches),
        ),
        running_mcps=running_mcps,
        configured_not_running=configured_not_running,
        running_not_configured=running_not_configured,
        live_suites=live_suites,
        orphan_suites=orphan_suites,
        stale_attached_branches=stale_attached_branches,
    )


def _build_running_mcp_summaries(
    *,
    live_suites: tuple[ProcessSuite, ...],
    orphan_suites: tuple[ProcessSuite, ...],
) -> tuple[RunningMcpSummary, ...]:
    instances = [
        *(_RunningInstance(branch.tool_signature, suite.live_codex_pid) for suite in live_suites for branch in build_attached_branches(suite)),
        *(
            _RunningInstance(infer_tool_signature(suite.processes[0].command_line), None)
            for suite in orphan_suites
            if suite.processes
        ),
    ]
    stale_signatures = {
        stale.tool_signature
        for suite in live_suites
        for stale in find_stale_attached_branches(suite)
    }
    grouped: dict[str, list[_RunningInstance]] = {}
    for instance in instances:
        grouped.setdefault(instance.tool_signature, []).append(instance)
    return tuple(
        RunningMcpSummary(
            tool_signature=tool_signature,
            instance_count=len(grouped[tool_signature]),
            live_codex_pid_count=len({item.live_codex_pid for item in grouped[tool_signature] if item.live_codex_pid}),
            has_stale=tool_signature in stale_signatures,
        )
        for tool_signature in sorted(grouped)
    )


def _configured_signatures(records: tuple[McpRecord, ...]) -> set[str]:
    return {
        signature
        for record in records
        if (signature := infer_record_tool_signature(record)) != "unknown"
    }
