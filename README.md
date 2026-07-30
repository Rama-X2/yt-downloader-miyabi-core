# YouTube Downloader - Miyabi Core

[![Implementation](https://img.shields.io/badge/Implementation-Original-brightgreen.svg)](#)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

A professional Windows terminal (CLI) application for downloading YouTube video, audio, and thumbnails, built on the yt-dlp Python API, external FFmpeg, and external aria2. Original implementation — no code or assets from any third-party downloader were copied.

> **Note on Original Implementation:** This project is an original codebase created independently without copying code, templates, or assets from any third-party tools.

---

## Setup

Follow these steps to set up and run the project:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/yt-downloader-miyabi-core.git
   cd yt-downloader-miyabi-core
   ```

2. **Configuration Setup:**
   Copy `config.example.json` to create `config.json`, or simply launch the application directly (it will automatically generate `config.json` with portable default settings):
   ```bash
   cp config.example.json config.json
   ```

3. **Download External Binaries (FFmpeg & aria2):**
   Download FFmpeg and aria2 manually from their official sites:
   - **FFmpeg**: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
   - **aria2**: [https://github.com/aria2/aria2/releases](https://github.com/aria2/aria2/releases)

   Extract the downloaded files into the project structure:
   - Extract FFmpeg binaries (`ffmpeg.exe`, `ffprobe.exe`) into `ffmpeg/bin/`
   - Extract aria2 binary (`aria2c.exe`) into `aria2/`

4. **Install Dependencies & Run:**
   ```bash
   pip install -r requirements.txt
   python launcher.py
   ```
   *Requires Python 3.10+.*

---

## Features

- Rich-powered terminal UI with a green/white theme
- Splash screen with live startup checks (yt-dlp, FFmpeg, aria2)
- Metadata lookup (title, channel, duration, upload date) via yt-dlp's Python API (no CLI-output scraping)
- Separate video-format and audio-format tables with resolution, codec, fps/bitrate, and file size
- Video download using aria2 as the external fragment downloader and FFmpeg for muxing/merging
- Audio download with optional MP3 conversion via FFmpeg
- Highest-resolution thumbnail download
- `yt-dlp -U` style self-update (standalone binary or pip package)
- Configurable settings persisted to `config.json`
- Timestamped log files written to `Logs/`

---

## Folder layout

```
yt-downloader-miyabi-core/
├── launcher.py            # entry point
├── config.json             # user configuration (auto-created if missing)
├── config.example.json     # reference configuration structure
├── requirements.txt
├── LICENSE
├── Source/
│   ├── __init__.py
│   ├── utils.py            # config, logging, formatting, env checks
│   ├── banner.py            # ASCII logo / branding
│   ├── splash.py             # startup screen + checks
│   ├── menu.py                # main menu loop / dispatch
│   ├── downloader.py           # metadata, format tables, video/audio DL
│   ├── thumbnail.py             # thumbnail download
│   ├── settings.py               # settings editor
│   └── updater.py                 # yt-dlp update routine
├── Assets/
├── Config/
├── Downloads/
├── Logs/
└── Temp/
```

By default the app expects the external tools at:

```
yt-dlp.exe
aria2/aria2c.exe
ffmpeg/bin/ffmpeg.exe
ffmpeg/bin/ffprobe.exe
```

These paths are stored in `config.json` under `"paths"` and can be changed there directly, or the app will fall back to searching your system `PATH` for `ffmpeg` / `aria2c` if the configured path is missing.

---

## Building a single EXE with PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --console --name "YouTube-Downloader" ^
    --add-data "config.json;." ^
    launcher.py
```

The resulting `dist/YouTube-Downloader.exe` can be placed anywhere; on first run it will create `config.json`, `Downloads/`, `Logs/`, and `Temp/` relative to wherever the EXE is located.

---

## Notes

- All downloads are saved by default into the configured `downloads_dir` (see Settings, option 1, to change it).
- If aria2 is not detected, the app automatically falls back to yt-dlp's built-in downloader.
- If FFmpeg is not detected, video+audio merging and MP3 conversion are disabled with a clear on-screen warning.

---

## Disclaimer

Tool ini dibuat untuk keperluan edukasi dan penggunaan pribadi/legal. Pengguna bertanggung jawab penuh untuk memastikan penggunaan tool ini sesuai dengan Terms of Service YouTube serta hukum hak cipta yang berlaku di wilayah masing-masing. Developer tidak bertanggung jawab atas penyalahgunaan tool ini.
