from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from codexsubmcp.core.analysis import AnalysisResult


ORPHAN_SUITE = "orphan_suite"


@dataclass(frozen=True)
class CleanupTarget:
    target_id: str
    target_type: str
    created_at: datetime
    kill_pid: int
    process_ids: tuple[int, ...]
    reason: str
    risk_hint: str
    suite_id: str | None = None


@dataclass(frozen=True)
class CleanupPreviewSummary:
    target_count: int


@dataclass(frozen=True)
class CleanupPreview:
    snapshot_id: str
    previewed_at: datetime
    summary: CleanupPreviewSummary
    targets: tuple[CleanupTarget, ...]


@dataclass(frozen=True)
class CleanupTargetResult:
    target_id: str
    target_type: str
    status: str
    killed_root_pid: int | None
    killed_process_ids: tuple[int, ...]
    error: str | None = None


@dataclass(frozen=True)
class CleanupResultSummary:
    success: bool
    target_count: int
    failed_target_count: int
    closed_suite_count: int
    killed_mcp_instance_count: int
    killed_process_count: int


@dataclass(frozen=True)
class CleanupResult:
    snapshot_id: str
    executed_at: datetime
    summary: CleanupResultSummary
    target_results: tuple[CleanupTargetResult, ...]


def build_cleanup_preview(analysis: AnalysisResult | None) -> CleanupPreview:
    if analysis is None:
        raise ValueError("analysis result is required before building cleanup preview")
    targets = tuple(
        sorted(
            [_orphan_target(suite) for suite in analysis.orphan_suites],
            key=lambda item: (item.created_at, item.target_id),
        )
    )
    return CleanupPreview(
        snapshot_id=analysis.snapshot_id,
        previewed_at=datetime.now(),
        summary=CleanupPreviewSummary(target_count=len(targets)),
        targets=targets,
    )


def execute_cleanup_preview(
    preview: CleanupPreview,
    *,
    kill_runner: Callable[[int], None],
) -> CleanupResult:
    results = tuple(_execute_target(target, kill_runner=kill_runner) for target in preview.targets)
    failed_count = sum(1 for item in results if item.status == "failed")
    closed_suite_count = _count_successes(results, ORPHAN_SUITE)
    killed_process_count = sum(len(item.killed_process_ids) for item in results)
    return CleanupResult(
        snapshot_id=preview.snapshot_id,
        executed_at=datetime.now(),
        summary=CleanupResultSummary(
            success=failed_count == 0,
            target_count=len(preview.targets),
            failed_target_count=failed_count,
            closed_suite_count=closed_suite_count,
            killed_mcp_instance_count=closed_suite_count,
            killed_process_count=killed_process_count,
        ),
        target_results=results,
    )


def _orphan_target(suite) -> CleanupTarget:
    return CleanupTarget(
        target_id=suite.suite_id,
        target_type=ORPHAN_SUITE,
        created_at=suite.created_at,
        kill_pid=suite.root_pid,
        process_ids=tuple(suite.process_ids),
        suite_id=suite.suite_id,
        reason="Codex 父进程已退出，该 orphan suite 可以整体回收。",
        risk_hint="会递归终止 suite root 及其后代进程。",
    )


def _execute_target(
    target: CleanupTarget,
    *,
    kill_runner: Callable[[int], None],
) -> CleanupTargetResult:
    try:
        kill_runner(target.kill_pid)
    except Exception as exc:  # noqa: BLE001
        return CleanupTargetResult(
            target_id=target.target_id,
            target_type=target.target_type,
            status="failed",
            killed_root_pid=None,
            killed_process_ids=(),
            error=str(exc),
        )
    return CleanupTargetResult(
        target_id=target.target_id,
        target_type=target.target_type,
        status="killed",
        killed_root_pid=target.kill_pid,
        killed_process_ids=target.process_ids,
    )


def _count_successes(results: tuple[CleanupTargetResult, ...], target_type: str) -> int:
    return sum(1 for item in results if item.target_type == target_type and item.status == "killed")
