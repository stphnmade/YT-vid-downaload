$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Require-Command {
  param([string]$Name, [string]$Hint)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Host "$Name is required but was not found on PATH."
    if ($Hint) {
      Write-Host $Hint
    }
    exit 1
  }
}

Require-Command -Name "node" -Hint "Install Node.js from https://nodejs.org/"
Require-Command -Name "npm" -Hint "npm ships with Node.js."

$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
  $pythonCmd = "python3"
} else {
  Write-Host "Python is required but was not found on PATH."
  exit 1
}

Write-Host "Installing Python dependencies..."
& $pythonCmd -m pip install -r (Join-Path $rootDir "services\downloader\requirements.txt")

$nodeModulesPath = Join-Path $rootDir "apps\desktop\node_modules"
if (Test-Path $nodeModulesPath) {
  $cleanAnswer = Read-Host "Remove existing node_modules to reduce size? (y/N)"
  if ($cleanAnswer -eq "y" -or $cleanAnswer -eq "Y") {
    Remove-Item -Recurse -Force $nodeModulesPath
  }
}

Write-Host "Installing desktop dependencies..."
Push-Location (Join-Path $rootDir "apps\desktop")
npm install
Pop-Location

if (-not (Get-Command "ffmpeg" -ErrorAction SilentlyContinue)) {
  Write-Host "Warning: FFmpeg not found. MP3 extraction will fail without it."
}

$answer = Read-Host "Start the app now? (y/N)"
if ($answer -eq "y" -or $answer -eq "Y") {
  Push-Location (Join-Path $rootDir "apps\desktop")
  npm run dev
  Pop-Location
} else {
  Write-Host "Setup complete. Run the app later with: cd apps/desktop; npm run dev"
}
