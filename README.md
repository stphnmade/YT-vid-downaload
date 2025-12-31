# YT Download App

Minimal cross-platform desktop app (Windows + macOS) for downloading YouTube MP4
video or MP3 audio. Paste a link, pick a format, track progress, and open the
file or folder from the recent history list.

## Requirements
- Node.js 18+
- Python 3.10+ (only needed when running the backend locally)
- FFmpeg (required for MP3 extraction)
- Docker (optional, for containerized backend)

## Local development
1. Install Python dependencies:
   `python -m pip install -r services/downloader/requirements.txt`
2. Install desktop dependencies:
   `cd apps/desktop; npm install`
3. Run the app:
   `npm run dev`

## Run backend in Docker
Use the helper scripts:
- `./docker-run.sh`
- `\.\docker-run.ps1`

Or manually:
1. `docker compose up -d --build`
2. Start Electron using the container API:
   - Bash: `YT_DOWNLOADER_API_URL=http://127.0.0.1:4545 npm run dev`
   - PowerShell: `$env:YT_DOWNLOADER_API_URL='http://127.0.0.1:4545'; npm run dev`

## Troubleshooting
- YouTube "confirm you're not a bot" errors can require cookies. Options:
  - `YT_DLP_COOKIES=/path/to/cookies.txt`
  - `YT_DLP_COOKIES_BROWSER=chrome` (or edge/firefox)
  - `services/downloader/yt-dlp.conf` (default uses `--cookies-from-browser chrome`)
    - Change the browser there or set `YT_DLP_CONFIG=/path/to/yt-dlp.conf`
  - Local backend will auto-detect Chrome/Edge/Firefox cookies if present.
  - Docker: set `YT_DLP_COOKIES_PATH` and use `docker-compose.cookies.yml`
    - Bash: `YT_DLP_COOKIES_PATH=/path/to/cookies.txt docker compose -f docker-compose.yml -f docker-compose.cookies.yml up -d --build`
    - PowerShell: `$env:YT_DLP_COOKIES_PATH='C:\path\to\cookies.txt'; docker compose -f docker-compose.yml -f docker-compose.cookies.yml up -d --build`

## Build
From `apps/desktop`:
`npm run dist`

