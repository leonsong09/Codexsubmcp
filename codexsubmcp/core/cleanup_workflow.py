from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codexsubmcp.core.analysis import AnalysisResult


ORPHAN_SUITE = "orphan_suite"
STALE_ATTACHED_BRANCH = "stale_attached_branch"


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
    tool_signature: str | None = None
    live_codex_pid: int | None = None
    latest_kept_launcher_pid: int | None = None


@dataclass(frozen=True)
class CleanupPreviewSummary:
    target_count: int
    orphan_suite_target_count: int
    stale_branch_target_count: int


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
    closed_stale_branch_count: int
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
    targets = tuple(sorted(_build_targets(analysis), key=lambda item: (item.created_at, item.target_id)))
    orphan_count = sum(1 for target in targets if target.target_type == ORPHAN_SUITE)
    stale_count = sum(1 for target in targets if target.target_type == STALE_ATTACHED_BRANCH)
    return CleanupPreview(
        snapshot_id=analysis.snapshot_id,
        previewed_at=datetime.now(),
        summary=CleanupPreviewSummary(
            target_count=len(targets),
            orphan_suite_target_count=orphan_count,
            stale_branch_target_count=stale_count,
        ),
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
    closed_stale_count = _count_successes(results, STALE_ATTACHED_BRANCH)
    killed_process_count = sum(len(item.killed_process_ids) for item in results)
    return CleanupResult(
        snapshot_id=preview.snapshot_id,
        executed_at=datetime.now(),
        summary=CleanupResultSummary(
            success=failed_count == 0,
            target_count=len(preview.targets),
            failed_target_count=failed_count,
            closed_suite_count=closed_suite_count,
            closed_stale_branch_count=closed_stale_count,
            killed_mcp_instance_count=closed_suite_count + closed_stale_count,
            killed_process_count=killed_process_count,
        ),
        target_results=results,
    )


def _build_targets(analysis: AnalysisResult) -> list[CleanupTarget]:
    return [
        *[_orphan_target(suite) for suite in analysis.orphan_suites],
        *[_stale_target(branch) for branch in analysis.stale_attached_branches],
    ]


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


def _stale_target(branch) -> CleanupTarget:
    return CleanupTarget(
        target_id=f"stale-{branch.live_codex_pid}-{branch.tool_signature}-{branch.launcher_pid}",
        target_type=STALE_ATTACHED_BRANCH,
        created_at=branch.created_at,
        kill_pid=branch.launcher_pid,
        process_ids=tuple(branch.process_ids),
        tool_signature=branch.tool_signature,
        live_codex_pid=branch.live_codex_pid,
        latest_kept_launcher_pid=branch.latest_kept_launcher_pid,
        reason=f"同一 Codex 会话下 {branch.tool_signature} 存在更新分支，当前分支已 stale。",
        risk_hint=f"仅清理旧分支，保留最新 launcher {branch.latest_kept_launcher_pid}。",
    )


def _execute_target(target: CleanupTarget, *, kill_runner: Callable[[int], None]) -> CleanupTargetResult:
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
