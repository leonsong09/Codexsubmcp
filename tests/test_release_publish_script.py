from __future__ import annotations

from pathlib import Path


def test_publish_release_script_uses_api_upload_and_temp_build_dirs(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    script = (project_root / "scripts" / "publish-release.ps1").read_text(encoding="utf-8")

    assert "PyInstaller" in script
    assert "--distpath" in script
    assert "temp\\release-publish\\$Tag" in script
    assert 'Invoke-ReleaseApi -Method "POST"' in script
    assert 'https://api.github.com/repos/$RepoSlug/releases' in script
    assert "curl.exe" in script
    assert "uploads.github.com/repos/$RepoSlug/releases/$ReleaseId/assets?name=$AssetName" in script
    assert '"release", "download"' in script
    assert "Downloaded exe hash mismatch" in script


def test_readme_references_latest_release_docs(
    project_root: Path = Path(__file__).resolve().parents[1],
):
    readme = (project_root / "README.md").read_text(encoding="utf-8")

    assert "docs/release-notes/2026-03-28-v0.3.0-cleanup-redesign.md" in readme
    assert "docs/release-announcements/2026-03-28-v0.3.0-end-user.md" in readme
    assert "docs/release-process.md" in readme
