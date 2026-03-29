[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [Parameter(Mandatory = $true)]
    [string]$Title,

    [Parameter(Mandatory = $true)]
    [string]$NotesFile,

    [string]$Repository = "",

    [switch]$ReplaceExistingRelease,

    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Invoke-CheckedCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [hashtable]$Environment = @{}
    )

    $envBackup = @{}
    foreach ($key in $Environment.Keys) {
        $envBackup[$key] = [Environment]::GetEnvironmentVariable($key)
        [Environment]::SetEnvironmentVariable($key, $Environment[$key])
    }

    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        foreach ($key in $Environment.Keys) {
            [Environment]::SetEnvironmentVariable($key, $envBackup[$key])
        }
    }
}

function Get-RepoSlug {
    $slug = (& gh repo view --json nameWithOwner --jq .nameWithOwner).Trim()
    if (-not $slug) {
        throw "Unable to determine GitHub repository slug."
    }
    return $slug
}

function Get-PythonCommand {
    $venvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Get-TagCommit {
    $commit = (& git rev-parse "$Tag^{commit}").Trim()
    if (-not $commit) {
        throw "Unable to resolve commit for tag $Tag"
    }
    return $commit
}

function Assert-RemoteTagExists {
    $remoteTag = (& git ls-remote --tags origin "refs/tags/$Tag").Trim()
    if (-not $remoteTag) {
        throw "Remote tag $Tag not found on origin. Push the tag first."
    }
}

function Get-Headers {
    $token = (& gh auth token).Trim()
    if (-not $token) {
        throw "Unable to retrieve GitHub token from gh auth token."
    }
    return @{
        Authorization = "Bearer $token"
        Accept = "application/vnd.github+json"
        "User-Agent" = "codexsubmcp-release-script"
    }
}

function Invoke-ReleaseApi {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body = $null,
        [string]$ContentType = "application/json"
    )

    $headers = Get-Headers
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
    }

    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -Body $Body -ContentType $ContentType
}

function Remove-ReleaseIfRequested {
    param([string]$RepoSlug)

    $exists = $false
    try {
        & gh release view $Tag -R $RepoSlug 1> $null 2> $null
        $exists = $LASTEXITCODE -eq 0
    }
    catch {
        $message = $_.Exception.Message
        if ($message -notmatch "release not found") {
            throw
        }
    }

    if (-not $exists) {
        return
    }

    if (-not $ReplaceExistingRelease) {
        throw "Release $Tag already exists. Re-run with -ReplaceExistingRelease to recreate it."
    }

    Write-Step "Deleting existing release $Tag"
    Invoke-CheckedCommand "gh" @("release", "delete", $Tag, "-R", $RepoSlug, "--yes")
}

function New-Release {
    param(
        [string]$RepoSlug,
        [string]$NotesContent,
        [string]$TargetCommit
    )

    $payload = @{
        tag_name = $Tag
        target_commitish = $TargetCommit
        name = $Title
        body = $NotesContent
        draft = $false
        prerelease = $false
        make_latest = "true"
    } | ConvertTo-Json -Depth 5

    return Invoke-ReleaseApi -Method "POST" -Uri "https://api.github.com/repos/$RepoSlug/releases" -Body $payload
}

function Upload-Asset {
    param(
        [string]$RepoSlug,
        [int]$ReleaseId,
        [string]$AssetPath,
        [string]$AssetName,
        [string]$ContentType,
        [switch]$SlowUpload
    )

    $token = (& gh auth token).Trim()
    $uploadUrl = "https://uploads.github.com/repos/$RepoSlug/releases/$ReleaseId/assets?name=$AssetName"
    $curlArgs = @(
        "--retry", "2",
        "--retry-all-errors",
        "--retry-delay", "2",
        "--silent",
        "--show-error",
        "--fail",
        "-X", "POST",
        "-H", "Authorization: Bearer $token",
        "-H", "Accept: application/vnd.github+json",
        "-H", "Content-Type: $ContentType",
        "--data-binary", "@$AssetPath",
        $uploadUrl
    )

    if ($SlowUpload) {
        $curlArgs = @("--limit-rate", "1M") + $curlArgs
    }

    & curl.exe @curlArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Asset upload failed for $AssetName"
    }
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Require-Command "git"
Require-Command "gh"
Require-Command "curl.exe"

if (-not (Test-Path $NotesFile)) {
    throw "Notes file not found: $NotesFile"
}

if (-not $Repository) {
    $Repository = Get-RepoSlug
}

$PythonCommand = Get-PythonCommand
$NotesContent = Get-Content $NotesFile -Raw -Encoding utf8
$TargetCommit = Get-TagCommit

Write-Step "Checking remote tag"
Assert-RemoteTagExists

if (-not $SkipTests) {
    Write-Step "Running pytest -q"
    Invoke-CheckedCommand $PythonCommand @("-m", "pytest", "-q") @{ QT_QPA_PLATFORM = "offscreen" }
}

$PublishRoot = Join-Path $ProjectRoot "temp\release-publish\$Tag"
$BuildDist = Join-Path $PublishRoot "dist"
$BuildWork = Join-Path $PublishRoot "build"
$VerifyDir = Join-Path $PublishRoot "verify"

Remove-Item -LiteralPath $PublishRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $BuildDist, $BuildWork, $VerifyDir | Out-Null

Write-Step "Building release artifact in temp output"
Invoke-CheckedCommand $PythonCommand @(
    "-m", "PyInstaller",
    "packaging/windows/CodexSubMcpManager.spec",
    "--noconfirm",
    "--clean",
    "--distpath", $BuildDist,
    "--workpath", $BuildWork
)

$ExePath = Join-Path $BuildDist "CodexSubMcpManager.exe"
$ChecksumPath = Join-Path $BuildDist "checksums.txt"

if (-not (Test-Path $ExePath)) {
    throw "Expected exe not found: $ExePath"
}

$ExeHash = Get-Sha256 $ExePath
Set-Content -NoNewline -Path $ChecksumPath -Value "$ExeHash  CodexSubMcpManager.exe"

Write-Step "Recreating release if needed"
Remove-ReleaseIfRequested -RepoSlug $Repository

Write-Step "Creating release"
$release = New-Release -RepoSlug $Repository -NotesContent $NotesContent -TargetCommit $TargetCommit

Write-Step "Uploading exe"
Upload-Asset -RepoSlug $Repository -ReleaseId $release.id -AssetPath $ExePath -AssetName "CodexSubMcpManager.exe" -ContentType "application/octet-stream" -SlowUpload

Write-Step "Uploading checksums"
Upload-Asset -RepoSlug $Repository -ReleaseId $release.id -AssetPath $ChecksumPath -AssetName "checksums.txt" -ContentType "text/plain; charset=utf-8"

Write-Step "Downloading release assets for verification"
Invoke-CheckedCommand "gh" @("release", "download", $Tag, "-R", $Repository, "-p", "CodexSubMcpManager.exe", "-p", "checksums.txt", "-D", $VerifyDir)

$DownloadedExe = Join-Path $VerifyDir "CodexSubMcpManager.exe"
$DownloadedChecksum = Join-Path $VerifyDir "checksums.txt"

$DownloadedHash = Get-Sha256 $DownloadedExe
$DownloadedChecksumLine = (Get-Content $DownloadedChecksum -Raw -Encoding utf8).Trim()
$ExpectedChecksumLine = "$ExeHash  CodexSubMcpManager.exe"

if ($DownloadedHash -ne $ExeHash) {
    throw "Downloaded exe hash mismatch. Expected $ExeHash, got $DownloadedHash"
}

if ($DownloadedChecksumLine -ne $ExpectedChecksumLine) {
    throw "Downloaded checksums.txt mismatch. Expected '$ExpectedChecksumLine', got '$DownloadedChecksumLine'"
}

$DistDir = Join-Path $ProjectRoot "dist"
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
try {
    Copy-Item -LiteralPath $ExePath -Destination (Join-Path $DistDir "CodexSubMcpManager.exe") -Force
    Copy-Item -LiteralPath $ChecksumPath -Destination (Join-Path $DistDir "checksums.txt") -Force
}
catch {
    Write-Warning "Release assets are published, but local dist copy failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Release published successfully." -ForegroundColor Green
Write-Host "Release URL: $($release.html_url)"
Write-Host "SHA256: $ExeHash"
