$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Host "HeyGent is not installed yet. Running setup first."
    & (Join-Path $ProjectRoot "setup.ps1")
}

$ForwardArgs = @($args)
if ($ForwardArgs.Count -eq 0) {
    $ForwardArgs = @("cli")
}

Push-Location $ProjectRoot
try {
    & $PythonPath -m app.heygent @ForwardArgs
} finally {
    Pop-Location
}
exit $LASTEXITCODE
