from __future__ import annotations

from pathlib import Path


def test_release_workflow_uses_node24_compatible_release_steps(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    workflow = (project_root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "uses: actions/checkout@v6" in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert "uses: softprops/action-gh-release" not in workflow
    assert "gh release upload" in workflow
