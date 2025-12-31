# agents.md

## Cross Platform YouTube Downloader Desktop App (MVP)

### Project codename

YT Download App

---

## 1. Product vision

A fast, minimal desktop app that lets users download YouTube videos or audio locally.  
The experience is calm and simple. Paste a link, choose MP4 or MP3, watch a clean progress bar, and find the file in Downloads. The app remembers preferences and shows a short history of recent downloads.

This MVP prioritizes reliability, clarity, and contributor friendliness over feature breadth.

---

## 2. MVP scope lock (do not expand without approval)

### Supported features

- Platforms: macOS and Windows
- Input: YouTube URLs only
- Formats: MP4 video or MP3 audio
- One download at a time
- Default save location: OS Downloads folder
- User can change save location and it persists
- Simple progress bar with percent text
- Download history list (recent items)
- Open file and open folder actions
- Cancel active download

### Explicit non goals

- No batch downloads
- No multiple concurrent downloads
- No account system
- No cloud storage
- No non YouTube platforms
- No advanced encoding options
- No login or analytics

---

## 3. UX flow

### First launch

1. App opens to main screen directly
2. Save path defaults to OS Downloads
3. No onboarding wizard for MVP

### Standard flow

1. User pastes YouTube link
2. User selects MP4 or MP3
3. User clicks Download
4. Progress bar updates with percent
5. On success, file saved to Downloads
6. History list updates

### Error flow

- Invalid URL shows inline error
- Non YouTube URL rejected
- Download failure shows readable message
- Error item appears in history

---

## 4. UI and design rules

### Visual style

- Minimalist, single card centered layout
- Sprite like or pixel inspired font allowed for headers
- Standard readable font for body text
- Neutral color palette
- Focus on clarity over decoration

### Iconography

- Use Lucide React and or Heroicons React
- Icons for actions only, not decoration

### Layout rules

- No unnecessary scrolling
- History panel may scroll internally if needed
- Disable inputs during active download

---

## 5. Technical architecture

### High level

- Electron for desktop shell and UI
- React for renderer UI
- Python backend using yt-dlp
- Local HTTP API between Electron and Python
- Python process launched and managed by Electron

### Data flow

Renderer → Electron IPC → Python HTTP API  
Python → Electron → Renderer UI update

---

## 6. Repository structure

```text
yt-download-app/
  apps/
    desktop/
      src/
        main/
        preload/
        renderer/
      package.json
      electron-builder.yml
  services/
    downloader/
      app/
        server.py
        ytdlp_runner.py
        validators.py
        models.py
      requirements.txt
  infra/
    docker/
      downloader.Dockerfile
    k8s/
      downloader-deployment.yaml
      downloader-service.yaml
  .github/
    workflows/
      ci.yml
      release.yml
  agents.md
  README.md
