Place packaged FFmpeg binaries here before building installers.

Expected bundle directories:
- `win32-x64/ffmpeg.exe` and `win32-x64/ffprobe.exe`
- `win32-arm64/ffmpeg.exe` and `win32-arm64/ffprobe.exe`
- `darwin-x64/ffmpeg` and `darwin-x64/ffprobe`
- `darwin-arm64/ffmpeg` and `darwin-arm64/ffprobe`
- `darwin-universal/ffmpeg` and `darwin-universal/ffprobe`

The recommended workflow is to set one of these environment variables and let the
builder hook stage the binaries automatically:
- `YT_DLP_FFMPEG_WIN_X64_SOURCE`
- `YT_DLP_FFMPEG_WIN_ARM64_SOURCE`
- `YT_DLP_FFMPEG_MAC_X64_SOURCE`
- `YT_DLP_FFMPEG_MAC_ARM64_SOURCE`
- `YT_DLP_FFMPEG_MAC_UNIVERSAL_SOURCE`

Or use the generic fallback:
- `YT_DLP_FFMPEG_SOURCE`

Each source should point to a directory that already contains the matching
`ffmpeg` and `ffprobe` binaries for that target.
