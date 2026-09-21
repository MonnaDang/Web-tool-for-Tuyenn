$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$outputRoot = Join-Path $projectRoot "dist"
$applicationRoot = Join-Path $outputRoot "TuyennnToolbox"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    python -m venv (Join-Path $projectRoot ".venv")
}

& $python -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt") pyinstaller

$binaryRoot = Join-Path $projectRoot "bin"

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "TuyennnToolbox" `
    --distpath $outputRoot `
    --workpath (Join-Path $projectRoot "build") `
    --specpath (Join-Path $projectRoot "build") `
    --add-data "$(Join-Path $PSScriptRoot 'resources');resources" `
    (Join-Path $PSScriptRoot "main.py")

$internalRoot = Join-Path $applicationRoot "_internal"
foreach ($incompatibleIcu in @("icuuc.dll", "icudt78.dll")) {
    $incompatiblePath = Join-Path $internalRoot $incompatibleIcu
    if (Test-Path -LiteralPath $incompatiblePath -PathType Leaf) {
        Remove-Item -LiteralPath $incompatiblePath -Force
    }
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "resources") -Destination $applicationRoot -Recurse -Force
Copy-Item -LiteralPath $binaryRoot -Destination $applicationRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $applicationRoot -Force

Write-Host ""
Write-Host "Portable application created at: $applicationRoot" -ForegroundColor Green
