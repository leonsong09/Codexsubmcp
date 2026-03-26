from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_limits_setuptools_package_discovery(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    package_find = pyproject["tool"]["setuptools"]["packages"]["find"]

    assert package_find["include"] == ["codexsubmcp*"]
    assert package_find["exclude"] == ["packaging*", "temp*"]
