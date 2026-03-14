# YT Download App

Minimal cross-platform desktop app (Windows + macOS) for downloading YouTube MP4
video or MP3 audio. Paste a link, pick a format, track progress, and open the
file or folder from the recent history list.

## Requirements
- Node.js 18+
- Python 3.10+ (only needed when running the backend locally)
- FFmpeg (required for MP3 extraction)
  - You can also point the backend at a bundled binary with `YT_DLP_FFMPEG_LOCATION`
- Docker (optional, for containerized backend)

## Local development
1. Install Python dependencies:
   `python -m pip install -r services/downloader/requirements.txt`
2. Install desktop dependencies:
   `cd apps/desktop; npm install`
3. Run the app:
   `npm run dev`

## Smoke test
Run a real MP4 + MP3 backend smoke test from the repo root:
`python scripts/smoke_downloads.py`

Useful options:
- `--ffmpeg-location /path/to/bin`
- `--format mp4 --format mp3`
- `--url https://www.youtube.com/watch?v=jNQXAC9IVRw`
- `--cookies /path/to/cookies.txt`
- `--cookies-browser chrome`

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
- If YouTube downloads suddenly start failing after previously working, update the
  pinned backend dependency:
  `python -m pip install -U yt-dlp`
- YouTube "confirm you're not a bot" errors can require cookies. Options:
  - `YT_DLP_COOKIES=/path/to/cookies.txt`
  - `YT_DLP_COOKIES_BROWSER=chrome` (or edge/firefox)
  - Close the browser before using `YT_DLP_COOKIES_BROWSER` if cookie import fails
  - `services/downloader/yt-dlp.conf` (default uses `--cookies-from-browser chrome`)
    - Change the browser there or set `YT_DLP_CONFIG=/path/to/yt-dlp.conf`
  - Local backend will auto-detect Chrome/Edge/Firefox cookies if present.
  - Docker: set `YT_DLP_COOKIES_PATH` and use `docker-compose.cookies.yml`
    - Bash: `YT_DLP_COOKIES_PATH=/path/to/cookies.txt docker compose -f docker-compose.yml -f docker-compose.cookies.yml up -d --build`
    - PowerShell: `$env:YT_DLP_COOKIES_PATH='C:\path\to\cookies.txt'; docker compose -f docker-compose.yml -f docker-compose.cookies.yml up -d --build`

## Build
From `apps/desktop`:
`npm run dist`

## Bundled FFmpeg for installers
Packaged Windows and macOS builds now expect a bundled FFmpeg pair so MP3 support
works out of the box. The Electron builder hook will fail packaging if the target
bundle is missing.

Supported bundle targets:
- `win32-x64`
- `win32-arm64`
- `darwin-x64`
- `darwin-arm64`
- `darwin-universal`

Set one of these environment variables to a directory containing `ffmpeg` and
`ffprobe` for the target you are packaging:
- `YT_DLP_FFMPEG_WIN_X64_SOURCE`
- `YT_DLP_FFMPEG_WIN_ARM64_SOURCE`
- `YT_DLP_FFMPEG_MAC_X64_SOURCE`
- `YT_DLP_FFMPEG_MAC_ARM64_SOURCE`
- `YT_DLP_FFMPEG_MAC_UNIVERSAL_SOURCE`

Or use:
- `YT_DLP_FFMPEG_SOURCE`

Optional manual staging step from `apps/desktop`:
`npm run prepare:ffmpeg -- win32-x64`

At runtime, the packaged app passes the bundled FFmpeg directory to the backend
through `YT_DLP_FFMPEG_LOCATION`.

