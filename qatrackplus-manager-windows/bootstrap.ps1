# QATrack+ Manager for Windows Bootstrap Script

$ErrorActionPreference = "Stop"

Write-Host "--- QATrack+ Manager for Windows Setup ---" -ForegroundColor Blue

# 1. Check for Python
$pythonExe = ""

function Find-Python {
    # Try 'python'
    try {
        $path = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($path -and $path -notmatch "WindowsApps") {
            return $path
        }
    } catch {}

    # Try 'py'
    try {
        $path = (Get-Command py -ErrorAction SilentlyContinue).Source
        if ($path) { return $path }
    } catch {}

    # Check common local paths
    $localPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
        "C:\Python*\python.exe",
        "C:\Program Files\Python*\python.exe"
    )
    foreach ($p in $localPaths) {
        $found = Get-ChildItem -Path $p -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($found) { return $found.FullName }
    }

    return ""
}

$pythonExe = Find-Python

if (-not $pythonExe) {
    Write-Host "Python was not found on your system." -ForegroundColor Yellow
    $choice = Read-Host "Would you like to install Python 3.12 via winget? (Y/N)"
    if ($choice -eq "Y" -or $choice -eq "y") {
        Write-Host "Installing Python 3.12 via winget... This may take a minute." -ForegroundColor Yellow
        winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
        
        # Re-check after installation
        $pythonExe = Find-Python
        if (-not $pythonExe) {
            Write-Host "Python was installed but still cannot be located. You may need to restart your terminal." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Error: Python is required to continue." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Using Python: $pythonExe" -ForegroundColor Green

# 1.5 Check for Git
$gitExe = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $gitExe) {
    Write-Host "Git was not found on your system." -ForegroundColor Yellow
    $choice = Read-Host "Would you like to install Git via winget? (Y/N)"
    if ($choice -eq "Y" -or $choice -eq "y") {
        Write-Host "Installing Git via winget..." -ForegroundColor Yellow
        winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements
        Write-Host "Git installed. You may need to restart your terminal for it to be in the PATH." -ForegroundColor Cyan
    }
}

# 2. Create Virtual Environment
$venvPath = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment in $venvPath..." -ForegroundColor Yellow
    & $pythonExe -m venv $venvPath
}

$pipExe = Join-Path $venvPath "Scripts\pip.exe"
$pythonVenvExe = Join-Path $venvPath "Scripts\python.exe"

# 3. Install/Upgrade Dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $pipExe install --upgrade pip setuptools wheel
& $pipExe install -e .

# 4. Create Run Script
$runScript = Join-Path $PSScriptRoot "run-manager.ps1"
@"
& "$pythonVenvExe" -m qatrackplus_manager_windows `$args
"@ | Out-File -FilePath $runScript -Encoding utf8

Write-Host "`nSetup Complete!" -ForegroundColor Green
Write-Host "To start the manager, run: ./run-manager.ps1" -ForegroundColor Cyan
