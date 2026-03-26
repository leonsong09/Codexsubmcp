from __future__ import annotations

import argparse
import sys
from typing import Sequence

from codexsubmcp.platform.windows.tasks import (
    DEFAULT_TASK_NAME,
    build_unregister_task_script as build_task_script,
    unregister_task,
)

def build_unregister_task_script(*, task_name: str) -> str:
    return build_task_script(task_name=task_name)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="卸载 Codex MCP watchdog 计划任务")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    args = parser.parse_args(argv)

    try:
        output = unregister_task(task_name=args.task_name)
    except RuntimeError as exc:
        print(str(exc) or "[ERROR] failed to unregister task", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
