param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ShimDirectory = (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"),
    [string]$ProfilePath = $PROFILE.CurrentUserCurrentHost,
    [switch]$SkipPackageInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$agentosExecutable = Join-Path $ProjectRoot ".venv\Scripts\agentos.exe"

if (-not $SkipPackageInstall) {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        python -m venv (Join-Path $ProjectRoot ".venv")
    }

    & $venvPython -m pip install -e "$ProjectRoot[dev]"
}

if (-not (Test-Path -LiteralPath $agentosExecutable)) {
    throw "AgentOS executable not found at $agentosExecutable. Run this script without -SkipPackageInstall."
}

if (-not (Test-Path -LiteralPath $ShimDirectory)) {
    New-Item -ItemType Directory -Path $ShimDirectory | Out-Null
}

$escapedExecutableForCmd = $agentosExecutable.Replace("%", "%%")
$shimPath = Join-Path $ShimDirectory "agentos.cmd"
$shim = @"
@echo off
"$escapedExecutableForCmd" %*
"@
Set-Content -LiteralPath $shimPath -Value $shim -Encoding ASCII

$startMarker = "# >>> agentos-personal command >>>"
$endMarker = "# <<< agentos-personal command <<<"
if (Test-Path -LiteralPath $ProfilePath) {
    $profileText = Get-Content -LiteralPath $ProfilePath -Raw
    $pattern = "(?s)" + [regex]::Escape($startMarker) + ".*?" + [regex]::Escape($endMarker)
    if ($profileText -match $pattern) {
        $profileText = [regex]::Replace($profileText, $pattern, "").TrimEnd() + [Environment]::NewLine
        Set-Content -LiteralPath $ProfilePath -Value $profileText -Encoding UTF8
    }
}

$pathEntries = $env:PATH -split ";" | ForEach-Object { $_.TrimEnd("\") }
$shimDirectoryInPath = $pathEntries -contains $ShimDirectory.TrimEnd("\")

Write-Output "AgentOS Personal command installed at $shimPath"
if (-not $shimDirectoryInPath) {
    Write-Output "Warning: $ShimDirectory is not currently in PATH. Add it to PATH or choose a PATH directory with -ShimDirectory."
}
Write-Output "Open a new terminal, then run: agentos version"
