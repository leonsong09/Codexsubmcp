from __future__ import annotations

from dataclasses import dataclass

from codexsubmcp.core.analysis import AnalysisResult
from codexsubmcp.core.system_snapshot import SystemSnapshot


@dataclass(frozen=True)
class RecognitionReport:
    status: str
    reason: str
    live_sample_count: int
    matched_codex_process_count: int
    verified_live_parent_count: int
    unmatched_live_parent_count: int

    @property
    def trusted(self) -> bool:
        return self.status == "trusted"


def validate_parent_recognition(
    snapshot: SystemSnapshot,
    analysis: AnalysisResult,
    config: dict[str, object],
) -> RecognitionReport:
    patterns = tuple(
        str(item).strip().lower()
        for item in (config.get("codex_patterns") or [])
        if str(item).strip()
    )
    matched_codex_process_count = sum(
        1 for process in snapshot.processes if _matches_codex_patterns(process.name, process.command_line, patterns)
    )
    live_parent_pids = sorted(
        {
            suite.live_codex_pid
            for suite in analysis.live_suites
            if suite.live_codex_pid is not None
        }
    )
    if not live_parent_pids:
        return RecognitionReport(
            status="blocked",
            reason="当前没有 live Codex 父进程样本，无法验证本机父进程识别规则。",
            live_sample_count=0,
            matched_codex_process_count=matched_codex_process_count,
            verified_live_parent_count=0,
            unmatched_live_parent_count=0,
        )

    process_map = {process.pid: process for process in snapshot.processes}
    unmatched = [
        pid
        for pid in live_parent_pids
        if not _matches_live_parent(process_map.get(pid), patterns)
    ]
    if unmatched:
        return RecognitionReport(
            status="blocked",
            reason="存在 live suite 无法回指到匹配的 Codex 父进程，已阻止 orphan 识别与清理。",
            live_sample_count=len(live_parent_pids),
            matched_codex_process_count=matched_codex_process_count,
            verified_live_parent_count=len(live_parent_pids) - len(unmatched),
            unmatched_live_parent_count=len(unmatched),
        )

    return RecognitionReport(
        status="trusted",
        reason="已用当前 live Codex 父进程样本验证识别规则，可以继续预览并清理 orphan。",
        live_sample_count=len(live_parent_pids),
        matched_codex_process_count=matched_codex_process_count,
        verified_live_parent_count=len(live_parent_pids),
        unmatched_live_parent_count=0,
    )


def _matches_live_parent(process, patterns: tuple[str, ...]) -> bool:
    if process is None:
        return False
    return _matches_codex_patterns(process.name, process.command_line, patterns)


def _matches_codex_patterns(name: str, command_line: str, patterns: tuple[str, ...]) -> bool:
    haystack = f"{name} {command_line}".lower()
    return any(pattern in haystack for pattern in patterns)
