from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from codexsubmcp.app_paths import build_runtime_paths
from codexsubmcp.core.analysis import AnalysisResult
from codexsubmcp.core.cleanup_workflow import CleanupPreview, CleanupResult
from codexsubmcp.core.recognition import RecognitionReport
from codexsubmcp.core.system_snapshot import SystemSnapshot


@dataclass(frozen=True)
class LifetimeStats:
    total_refresh_count: int = 0
    total_preview_count: int = 0
    total_cleanup_count: int = 0
    total_closed_suite_count: int = 0
    total_killed_mcp_instance_count: int = 0
    total_killed_process_count: int = 0
    last_cleanup_at: datetime | None = None


def write_refresh_log(
    *,
    snapshot: SystemSnapshot,
    analysis: AnalysisResult,
    recognition: RecognitionReport,
    log_dir: Path | None = None,
) -> Path:
    return _write_log(
        kind="refresh",
        happened_at=analysis.analyzed_at,
        payload={
            "kind": "refresh",
            "snapshot_id": snapshot.snapshot_id,
            "captured_at": snapshot.captured_at,
            "summary": {
                "open_subagent_count": snapshot.codex.open_subagent_count,
                "configured_mcp_count": analysis.summary.configured_mcp_count,
                "running_mcp_instance_count": analysis.summary.running_mcp_instance_count,
                "live_suite_count": analysis.summary.live_suite_count,
                "orphan_suite_count": analysis.summary.orphan_suite_count,
            },
            "recognition": recognition,
        },
        log_dir=log_dir,
    )


def write_preview_log(*, preview: CleanupPreview, log_dir: Path | None = None) -> Path:
    return _write_log(
        kind="preview",
        happened_at=preview.previewed_at,
        payload={
            "kind": "preview",
            "snapshot_id": preview.snapshot_id,
            "previewed_at": preview.previewed_at,
            "summary": preview.summary,
            "targets": preview.targets,
        },
        log_dir=log_dir,
    )


def write_cleanup_log(*, result: CleanupResult, log_dir: Path | None = None) -> Path:
    return _write_log(
        kind="cleanup",
        happened_at=result.executed_at,
        payload={
            "kind": "cleanup",
            "snapshot_id": result.snapshot_id,
            "executed_at": result.executed_at,
            "summary": result.summary,
            "target_results": result.target_results,
        },
        log_dir=log_dir,
    )


def load_lifetime_stats(*, log_dir: Path | None = None) -> LifetimeStats:
    stats = LifetimeStats()
    for path in sorted(_resolve_log_dir(log_dir).glob("*.json")):
        payload = _read_payload(path)
        kind = str(payload.get("kind") or "")
        if kind == "refresh":
            stats = _update_refresh_stats(stats)
            continue
        if kind == "preview":
            stats = _update_preview_stats(stats)
            continue
        if kind == "cleanup":
            stats = _update_cleanup_stats(stats, payload)
    return stats


def _write_log(*, kind: str, happened_at: datetime, payload: dict[str, Any], log_dir: Path | None) -> Path:
    path = _resolve_log_dir(log_dir) / f"{kind}-{happened_at.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(_serialize(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _resolve_log_dir(log_dir: Path | None) -> Path:
    resolved = log_dir or build_runtime_paths().logs
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _update_refresh_stats(stats: LifetimeStats) -> LifetimeStats:
    return LifetimeStats(**{**asdict(stats), "total_refresh_count": stats.total_refresh_count + 1})


def _update_preview_stats(stats: LifetimeStats) -> LifetimeStats:
    return LifetimeStats(**{**asdict(stats), "total_preview_count": stats.total_preview_count + 1})


def _update_cleanup_stats(stats: LifetimeStats, payload: dict[str, Any]) -> LifetimeStats:
    summary = payload.get("summary")
    if not isinstance(summary, dict) or not summary.get("success"):
        return stats
    executed_at = _parse_datetime(payload.get("executed_at"))
    return LifetimeStats(
        total_refresh_count=stats.total_refresh_count,
        total_preview_count=stats.total_preview_count,
        total_cleanup_count=stats.total_cleanup_count + 1,
        total_closed_suite_count=stats.total_closed_suite_count + int(summary.get("closed_suite_count") or 0),
        total_killed_mcp_instance_count=stats.total_killed_mcp_instance_count
        + int(summary.get("killed_mcp_instance_count") or 0),
        total_killed_process_count=stats.total_killed_process_count + int(summary.get("killed_process_count") or 0),
        last_cleanup_at=max(filter(None, [stats.last_cleanup_at, executed_at]), default=None),
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value)


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _serialize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value
