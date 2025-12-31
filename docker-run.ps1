$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 4545
$composeFile = Join-Path $rootDir "docker-compose.yml"
$composeCookiesFile = Join-Path $rootDir "docker-compose.cookies.yml"

$composeArgs = @("-f", $composeFile)

$cookiesPath = Read-Host "Path to cookies.txt (leave blank to skip)"
if ($cookiesPath) {
  if (-not (Test-Path $cookiesPath)) {
    Write-Host "cookies.txt not found at: $cookiesPath"
    exit 1
  }
  $env:YT_DLP_COOKIES_PATH = $cookiesPath
  $composeArgs += @("-f", $composeCookiesFile)
}

Write-Host "Stopping any previous Compose stack..."
try {
  docker compose @composeArgs down --remove-orphans | Out-Null
} catch {
}
try {
  docker rm -f yt-downloader-test 2>$null | Out-Null
} catch {
}

Write-Host "Starting services with Docker Compose..."
docker compose @composeArgs up -d --build

Write-Host "Checking health endpoint..."
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/health"
    if ($response.StatusCode -eq 200) {
      $ok = $true
      break
    }
  } catch {
    Start-Sleep -Milliseconds 500
  }
}

if (-not $ok) {
  Write-Host "Health check failed. Container logs:"
  docker compose @composeArgs logs downloader
  exit 1
}

Write-Host "Health check OK."
$startAnswer = Read-Host "Start the Electron app now? (y/N)"
if ($startAnswer -eq "y" -or $startAnswer -eq "Y") {
  $previousApiUrl = $env:YT_DOWNLOADER_API_URL
  $env:YT_DOWNLOADER_API_URL = "http://127.0.0.1:$port"
  Push-Location (Join-Path $rootDir "apps\desktop")
  npm run dev
  Pop-Location
  if ($null -ne $previousApiUrl -and $previousApiUrl -ne "") {
    $env:YT_DOWNLOADER_API_URL = $previousApiUrl
  } else {
    Remove-Item Env:YT_DOWNLOADER_API_URL -ErrorAction SilentlyContinue
  }
}

$answer = Read-Host "Stop and remove the containers now? (y/N)"
if ($answer -eq "y" -or $answer -eq "Y") {
  docker compose @composeArgs down
  Write-Host "Containers removed."
} else {
  Write-Host "Containers left running."
}
