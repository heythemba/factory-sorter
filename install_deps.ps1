Param(
    [string]$PythonExe = "py"  # try Windows Python Launcher by default
)

# Fail on errors
$ErrorActionPreference = "Stop"

function Have-Cmd([string]$cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

# Resolve Python executable
if (-not (Have-Cmd $PythonExe)) {
    Write-Host "Specified Python executable '$PythonExe' not found in PATH." -ForegroundColor Red
    Write-Host "Trying common alternatives: 'python', 'python3'..." -ForegroundColor Yellow
    if (Have-Cmd "python3") { $PythonExe = "python3" }
    elseif (Have-Cmd "python") { $PythonExe = "python" }
    else {
        Write-Error "No suitable Python executable found. Install Python from https://python.org and ensure it's in PATH."
        exit 1
    }
}

# Check pip; bootstrap if missing
$pipOk = $false
try {
    & $PythonExe -m pip --version | Out-Null
    $pipOk = $true
} catch {
    $pipOk = $false
}

if (-not $pipOk) {
    Write-Host "pip not found for '$PythonExe'. Attempting ensurepip..." -ForegroundColor Yellow
    try {
        & $PythonExe -m ensurepip --upgrade
        $pipOk = $true
    } catch {
        Write-Host "ensurepip failed. Bootstrapping with get-pip.py..." -ForegroundColor Yellow
        $getpip = Join-Path -Path (Get-Location) -ChildPath "get-pip.py"
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip -UseBasicParsing
        & $PythonExe $getpip
        Remove-Item $getpip -Force
    }
}

# Upgrade pip and install requirements
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt

Write-Host "All dependencies installed successfully for $PythonExe." -ForegroundColor Green
