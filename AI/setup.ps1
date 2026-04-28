$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"
$EnvPath = Join-Path $ProjectRoot ".env"
$EnvExamplePath = Join-Path $ProjectRoot ".env.example"

Set-Location $ProjectRoot

if (-not (Test-Path $PythonPath)) {
    Write-Host "[setup] Creating .venv"
    py -3.11 -m venv .venv
}

Write-Host "[setup] Installing Python dependencies"
& $PythonPath -m pip install --upgrade pip
& $PythonPath -m pip install -r requirements.txt

if ((-not (Test-Path $EnvPath)) -and (Test-Path $EnvExamplePath)) {
    Write-Host "[setup] Creating .env from .env.example"
    Copy-Item $EnvExamplePath $EnvPath
}

$LauncherPath = Join-Path $ProjectRoot "heygent.ps1"
Set-Alias -Name heygent -Value $LauncherPath -Scope Global

$ProfilePath = $PROFILE
$ProfileDir = Split-Path -Parent $ProfilePath
if (-not (Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir | Out-Null
}

$ProfileStart = "# >>> HeyGent AI Backbone >>>"
$ProfileEnd = "# <<< HeyGent AI Backbone <<<"
$ProfileBlock = @"
$ProfileStart
function heygent {
    & '$LauncherPath' @args
}
$ProfileEnd
"@

$ProfileContent = ""
if (Test-Path $ProfilePath) {
    $ProfileContent = Get-Content $ProfilePath -Raw
}

$EscapedStart = [regex]::Escape($ProfileStart)
$EscapedEnd = [regex]::Escape($ProfileEnd)
$ManagedBlockPattern = "(?s)$EscapedStart.*?$EscapedEnd"
if ($ProfileContent -match $ManagedBlockPattern) {
    $ProfileContent = [regex]::Replace($ProfileContent, $ManagedBlockPattern, $ProfileBlock)
} else {
    if ($ProfileContent.Trim().Length -gt 0) {
        $ProfileContent = $ProfileContent.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + $ProfileBlock
    } else {
        $ProfileContent = $ProfileBlock
    }
}
Set-Content -Path $ProfilePath -Value $ProfileContent -Encoding UTF8

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run:"
Write-Host "  heygent"
Write-Host ""
Write-Host "This also registers heygent in your PowerShell profile:"
Write-Host "  $ProfilePath"
