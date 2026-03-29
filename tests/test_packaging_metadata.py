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


def test_pyinstaller_spec_builds_windows_version_info_from_pyproject(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    spec = (project_root / "packaging" / "windows" / "CodexSubMcpManager.spec").read_text(encoding="utf-8")

    assert "tomllib" in spec
    assert 'PROJECT_ROOT / "pyproject.toml"' in spec
    assert "VSVersionInfo" in spec
    assert 'StringStruct("ProductVersion", version)' in spec
    assert "version=VERSION_INFO" in spec
