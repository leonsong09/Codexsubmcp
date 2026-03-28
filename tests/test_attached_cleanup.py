from __future__ import annotations

from datetime import datetime

from codexsubmcp.core.models import ProcessInfo, ProcessSuite
from codexsubmcp.core.stale_attached import find_stale_attached_branches


def _proc(
    pid: int,
    ppid: int,
    name: str,
    created_at: str,
    command_line: str,
) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        name=name,
        created_at=datetime.fromisoformat(created_at),
        command_line=command_line,
    )


def test_find_stale_attached_branches_keeps_latest_branch_per_tool() -> None:
    suite = ProcessSuite(
        suite_id="live-100",
        classification="attached_to_live_codex",
        created_at=datetime.fromisoformat("2026-03-28T10:00:00"),
        root_pid=110,
        live_codex_pid=100,
        processes=(
            _proc(110, 100, "cmd.exe", "2026-03-28T10:00:00", "cmd /c ace-tool.cmd --token t1"),
            _proc(111, 110, "node.exe", "2026-03-28T10:00:01", "node ace-tool index.js"),
            _proc(120, 100, "cmd.exe", "2026-03-28T10:01:00", "cmd /c npx -y agentation-mcp server"),
            _proc(121, 120, "node.exe", "2026-03-28T10:01:01", "node npx-cli.js -y agentation-mcp server"),
            _proc(122, 121, "cmd.exe", "2026-03-28T10:01:02", "cmd /d /s /c agentation-mcp server"),
            _proc(123, 122, "node.exe", "2026-03-28T10:01:03", "node agentation-mcp cli.js server"),
            _proc(
                210,
                100,
                "cmd.exe",
                "2026-03-28T10:10:00",
                "cmd /c npx -y @modelcontextprotocol/server-memory",
            ),
            _proc(211, 210, "node.exe", "2026-03-28T10:10:01", "node npx-cli.js -y server-memory"),
            _proc(310, 100, "cmd.exe", "2026-03-28T10:11:00", "cmd /c ace-tool.cmd --token t2"),
            _proc(311, 310, "node.exe", "2026-03-28T10:11:01", "node ace-tool index.js"),
            _proc(320, 100, "cmd.exe", "2026-03-28T10:12:00", "cmd /c npx -y agentation-mcp server"),
            _proc(321, 320, "node.exe", "2026-03-28T10:12:01", "node npx-cli.js -y agentation-mcp server"),
            _proc(322, 321, "cmd.exe", "2026-03-28T10:12:02", "cmd /d /s /c agentation-mcp server"),
            _proc(323, 322, "node.exe", "2026-03-28T10:12:03", "node agentation-mcp cli.js server"),
        ),
    )

    stale = find_stale_attached_branches(suite)

    assert [branch.tool_signature for branch in stale] == ["ace-tool", "agentation-mcp"]
    assert [branch.launcher_pid for branch in stale] == [110, 120]
    assert [branch.live_codex_pid for branch in stale] == [100, 100]
    assert [branch.latest_kept_launcher_pid for branch in stale] == [310, 320]
    assert stale[0].process_ids == [110, 111]
    assert stale[1].process_ids == [120, 121, 122, 123]


def test_find_stale_attached_branches_supports_playwright_and_devtools_signatures() -> None:
    suite = ProcessSuite(
        suite_id="live-200",
        classification="attached_to_live_codex",
        created_at=datetime.fromisoformat("2026-03-28T11:00:00"),
        root_pid=410,
        live_codex_pid=200,
        processes=(
            _proc(410, 200, "cmd.exe", "2026-03-28T11:00:00", "cmd /c npx -y @playwright/mcp@latest"),
            _proc(411, 410, "node.exe", "2026-03-28T11:00:01", "node npx-cli.js @playwright/mcp"),
            _proc(
                420,
                200,
                "cmd.exe",
                "2026-03-28T11:00:02",
                "cmd /c npx -y chrome-devtools-mcp@latest --browser-url=http://127.0.0.1:3600",
            ),
            _proc(421, 420, "node.exe", "2026-03-28T11:00:03", "node npx-cli.js chrome-devtools-mcp"),
            _proc(510, 200, "cmd.exe", "2026-03-28T11:10:00", "cmd /c npx -y @playwright/mcp@latest"),
            _proc(511, 510, "node.exe", "2026-03-28T11:10:01", "node npx-cli.js @playwright/mcp"),
        ),
    )

    stale = find_stale_attached_branches(suite)

    assert len(stale) == 1
    assert stale[0].tool_signature == "playwright-mcp"
    assert stale[0].launcher_pid == 410
    assert stale[0].process_ids == [410, 411]


def test_find_stale_attached_branches_ignores_orphan_suites() -> None:
    suite = ProcessSuite(
        suite_id="orphan-1",
        classification="orphaned_after_codex_exit",
        created_at=datetime.fromisoformat("2026-03-28T09:00:00"),
        root_pid=610,
        processes=(
            _proc(610, 9999, "cmd.exe", "2026-03-28T09:00:00", "cmd /c npx -y agentation-mcp server"),
            _proc(611, 610, "node.exe", "2026-03-28T09:00:01", "node npx-cli.js agentation-mcp"),
        ),
    )

    assert find_stale_attached_branches(suite) == []
