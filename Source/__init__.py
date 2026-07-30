"""
Source package for the RAMA SERVER - MIYABI CORE YouTube Downloader.

This package contains all the modular components of the application:
    - utils        : configuration, logging and shared helpers
    - banner        : ASCII art / branding rendering
    - splash        : startup splash screen and environment checks
    - menu          : main menu loop and navigation
    - downloader    : video/audio download logic (yt-dlp + aria2 + ffmpeg)
    - thumbnail     : thumbnail extraction and download
    - settings      : interactive settings editor
    - updater       : yt-dlp self-update routine
"""

__all__ = [
    "utils",
    "banner",
    "splash",
    "menu",
    "downloader",
    "thumbnail",
    "settings",
    "updater",
]
