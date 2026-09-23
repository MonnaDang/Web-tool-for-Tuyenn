$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$outputRoot = Join-Path $projectRoot "dist"
$applicationRoot = Join-Path $outputRoot "TuyennnToolbox"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = $null

if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    try {
        & $venvPython --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $python = $venvPython
        }
    } catch {
        $python = $null
    }
}

if (-not $python) {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $python = $pythonCommand.Source
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

$versionData = Get-Content -LiteralPath (Join-Path $PSScriptRoot "resources\version.json") -Raw | ConvertFrom-Json
$archivePath = Join-Path $outputRoot "TuyennnToolbox-win64.zip"
if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
Compress-Archive -LiteralPath $applicationRoot -DestinationPath $archivePath -CompressionLevel Optimal
$archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archivePath.sha256" -Value "$archiveHash  TuyennnToolbox-win64.zip" -Encoding ascii

Write-Host ""
Write-Host "Portable application created at: $applicationRoot" -ForegroundColor Green
Write-Host "Release archive created at: $archivePath" -ForegroundColor Green
Write-Host "Version: $($versionData.version)" -ForegroundColor Green
