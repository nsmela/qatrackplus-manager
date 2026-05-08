# QATrack+ Manager for Windows Bootstrap Script

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/nsmela/qatrackplus-manager.git"
$FOLDER_NAME = "qatrackplus-manager"

Write-Host "--- QATrack+ Manager for Windows Setup ---" -ForegroundColor Blue

# 1. Check for Git (Needed for cloning)
$gitExe = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $gitExe) {
    Write-Host "Git was not found on your system." -ForegroundColor Yellow
    $choice = Read-Host "Would you like to install Git via winget? (Y/N)"
    if ($choice -eq "Y" -or $choice -eq "y") {
        Write-Host "Installing Git via winget..." -ForegroundColor Yellow
        winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements
        # Refresh path for current session is hard in PS, inform user
        Write-Host "Git installed. You MUST restart your terminal for Git to be available in the PATH." -ForegroundColor Red
        Write-Host "After restarting, run this script again." -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "Error: Git is required to download the project." -ForegroundColor Red
        exit 1
    }
}

# 2. Handle Repository Context
$initialDir = Get-Location
$scriptDir = $PSScriptRoot

# Check if we are already in the project directory (look for pyproject.toml)
if (Test-Path (Join-Path $scriptDir "pyproject.toml")) {
    $projectRoot = $scriptDir
} elseif (Test-Path (Join-Path $initialDir "pyproject.toml")) {
    $projectRoot = $initialDir
} else {
    # Need to clone or find the cloned folder
    $parentDir = if ($scriptDir) { $scriptDir } else { $initialDir }
    $clonedDir = Join-Path $parentDir $FOLDER_NAME
    
    if (-not (Test-Path $clonedDir)) {
        Write-Host "Project files not found. Cloning from $REPO_URL..." -ForegroundColor Yellow
        Push-Location $parentDir
        & git clone $REPO_URL $FOLDER_NAME
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to clone repository." -ForegroundColor Red
            exit 1
        }
        Pop-Location
    }
    
    $projectRoot = Join-Path $clonedDir "qatrackplus-manager-windows"
}

if (-not (Test-Path $projectRoot)) {
    Write-Host "Error: Could not find qatrackplus-manager-windows directory at $projectRoot" -ForegroundColor Red
    exit 1
}

Write-Host "Setting up in: $projectRoot" -ForegroundColor Cyan
Set-Location $projectRoot

# 3. Check for Python
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

# 4. Create Virtual Environment
$venvPath = Join-Path $projectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment in $venvPath..." -ForegroundColor Yellow
    & $pythonExe -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

$pipExe = Join-Path $venvPath "Scripts\pip.exe"
$pythonVenvExe = Join-Path $venvPath "Scripts\python.exe"

# 5. Install/Upgrade Dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& "$pythonVenvExe" -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upgrade pip/setuptools/wheel." -ForegroundColor Red
    exit 1
}

& "$pythonVenvExe" -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install qatrackplus-manager-windows in editable mode." -ForegroundColor Red
    exit 1
}

# 6. Create Run Script
$runScript = Join-Path $projectRoot "run-manager.ps1"
@"
& "$pythonVenvExe" -m qatrackplus_manager_windows `$args
"@ | Out-File -FilePath $runScript -Encoding utf8

Write-Host "`nSetup Complete!" -ForegroundColor Green
Write-Host "To start the manager, run: cd '$projectRoot'; ./run-manager.ps1" -ForegroundColor Cyan
