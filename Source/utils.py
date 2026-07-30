"""
utils.py
--------
Shared utilities for YouTube Downloader - Miyabi Core.

Responsibilities:
    * Load / save the JSON configuration file.
    * Provide a pre-configured logging system that writes timestamped
      log files into the Logs folder.
    * Provide small formatting helpers (byte sizes, durations).
    * Provide environment/binary detection helpers (ffmpeg, ffprobe, aria2c).
    * Provide a single shared Rich Console instance using the project theme.

Every other module in Source/ should import from here instead of
re-implementing configuration or logging logic.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.theme import Theme

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

# The application root is the folder containing launcher.py (one level up
# from Source/). This makes the app portable and PyInstaller-friendly.
APP_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = APP_ROOT / "config.json"

# --------------------------------------------------------------------------
# Theme / Console
# --------------------------------------------------------------------------

RAMA_THEME = Theme(
    {
        "primary": "bold green",
        "secondary": "white",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "muted": "grey62",
        "accent": "bold bright_green",
    }
)

console = Console(theme=RAMA_THEME)

# --------------------------------------------------------------------------
# Default configuration (used if config.json is missing or corrupted)
# --------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "name": "YouTube Downloader",
        "brand": "Miyabi Core",
        "version": "1.0.0",
    },
    "paths": {
        "base_dir": str(APP_ROOT),
        "yt_dlp_exe": str(APP_ROOT / "yt-dlp.exe"),
        "yt_dlp_conf": str(APP_ROOT / "yt-dlp.conf"),
        "aria2c_exe": str(APP_ROOT / "aria2" / "aria2c.exe"),
        "ffmpeg_dir": str(APP_ROOT / "ffmpeg" / "bin"),
        "ffmpeg_exe": str(APP_ROOT / "ffmpeg" / "bin" / "ffmpeg.exe"),
        "ffprobe_exe": str(APP_ROOT / "ffmpeg" / "bin" / "ffprobe.exe"),
        "downloads_dir": str(APP_ROOT / "Downloads"),
        "logs_dir": str(APP_ROOT / "Logs"),
        "temp_dir": str(APP_ROOT / "Temp"),
        "assets_dir": str(APP_ROOT / "Assets"),
    },
    "download": {
        "use_aria2": True,
        "concurrent_fragments": 5,
        "aria2_max_connection_per_server": 16,
        "aria2_split": 16,
        "output_template": "%(title)s [%(id)s].%(ext)s",
        "audio_format": "mp3",
        "audio_quality": "192",
        "merge_output_format": "mp4",
    },
    "theme": {
        "primary": "green",
        "secondary": "white",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge `override` into `base`, returning `base`."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> dict[str, Any]:
    """
    Load config.json from the application root.

    If the file does not exist or is invalid JSON, a fresh copy of the
    default configuration is written to disk and returned, so the app
    never crashes on a missing/corrupt config.
    """
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                user_config = json.load(fh)
            config = _deep_merge(config, user_config)
        except (json.JSONDecodeError, OSError) as exc:
            console.print(
                f"[warning]Warning:[/warning] config.json could not be read "
                f"({exc}). Falling back to default configuration."
            )
    else:
        save_config(config)

    return config


def save_config(config: dict[str, Any]) -> None:
    """Persist the given configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=4, ensure_ascii=False)
    except OSError as exc:
        console.print(f"[error]Failed to save config.json:[/error] {exc}")


def ensure_directories(config: dict[str, Any]) -> None:
    """Make sure Downloads/Logs/Temp/Assets/Config directories exist."""
    for key in ("downloads_dir", "logs_dir", "temp_dir", "assets_dir"):
        path = Path(config["paths"].get(key, ""))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

_logger: Optional[logging.Logger] = None


def get_logger(config: Optional[dict[str, Any]] = None) -> logging.Logger:
    """
    Return a singleton logger that writes timestamped log files into the
    configured Logs directory, e.g. Logs/2026-07-25_143210.log
    """
    global _logger
    if _logger is not None:
        return _logger

    if config is None:
        config = load_config()

    logs_dir = Path(config["paths"].get("logs_dir", APP_ROOT / "Logs"))
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        logs_dir = APP_ROOT  # fallback

    log_filename = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".log"
    log_path = logs_dir / log_filename

    logger = logging.getLogger("miyabi_yt_downloader")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _logger = logger
    logger.info("Logger initialized. Log file: %s", log_path)
    return logger


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def format_bytes(size: Optional[float]) -> str:
    """Convert a byte count into a human readable string, e.g. '812 MB'."""
    if size is None or size <= 0:
        return "Unknown"

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024.0:
            if unit == "B":
                return f"{value:.0f} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def format_duration(seconds: Optional[float]) -> str:
    """Convert seconds into HH:MM:SS (or MM:SS if under an hour)."""
    if seconds is None:
        return "Unknown"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_upload_date(date_str: Optional[str]) -> str:
    """Convert yt-dlp's YYYYMMDD upload_date into YYYY-MM-DD."""
    if not date_str or len(date_str) != 8:
        return "Unknown"
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return "Unknown"


# --------------------------------------------------------------------------
# Binary detection
# --------------------------------------------------------------------------

def resolve_binary(configured_path: str, fallback_name: str) -> Optional[str]:
    """
    Resolve a binary path.

    First checks the explicit path from config.json. If that file does not
    exist, falls back to searching the system PATH for `fallback_name`
    (e.g. 'ffmpeg', 'aria2c'). Returns None if not found anywhere.
    """
    if configured_path and Path(configured_path).is_file():
        return configured_path

    found = shutil.which(fallback_name)
    if found:
        return found

    return None


def check_environment(config: dict[str, Any]) -> dict[str, Any]:
    """
    Run startup checks and return a dictionary describing the environment:
        {
            "yt_dlp_api": bool,
            "yt_dlp_version": str | None,
            "ffmpeg_path": str | None,
            "ffprobe_path": str | None,
            "aria2c_path": str | None,
        }
    """
    result: dict[str, Any] = {
        "yt_dlp_api": False,
        "yt_dlp_version": None,
        "ffmpeg_path": None,
        "ffprobe_path": None,
        "aria2c_path": None,
    }

    try:
        import yt_dlp  # noqa: WPS433 (local import by design)

        result["yt_dlp_api"] = True
        result["yt_dlp_version"] = getattr(yt_dlp.version, "__version__", "unknown")
    except ImportError:
        result["yt_dlp_api"] = False

    paths = config.get("paths", {})
    result["ffmpeg_path"] = resolve_binary(paths.get("ffmpeg_exe", ""), "ffmpeg")
    result["ffprobe_path"] = resolve_binary(paths.get("ffprobe_exe", ""), "ffprobe")
    result["aria2c_path"] = resolve_binary(paths.get("aria2c_exe", ""), "aria2c")

    return result


def clear_screen() -> None:
    """Clear the terminal screen in a cross-platform way."""
    os.system("cls" if os.name == "nt" else "clear")


# --------------------------------------------------------------------------
# Cancel-aware prompts
# --------------------------------------------------------------------------

# Typing any of these (case-insensitive) at a prompt cancels the current
# action and returns to the previous menu.
CANCEL_KEYWORDS = {"exit", "quit", "cancel", "batal", "kembali", "back"}


def prompt_input(label: str, hint: bool = True) -> Optional[str]:
    """
    Read a line of input for the given prompt label.

    Returns the stripped input string, or None if the user wants to go
    back: this happens if they type 'exit' (or cancel/batal/kembali/back),
    or simply press ENTER on an empty line. As a convenience, any input
    that later fails validation (e.g. an unknown format ID) should also
    be treated by the caller as "go back" - so typing anything that
    doesn't resolve to a valid choice, followed by ENTER, gets the user
    back to the previous screen without needing to retry.
    """
    suffix = " [muted](ketik 'exit' untuk kembali)[/muted]" if hint else ""
    try:
        raw = console.input(f"[primary]{label}[/primary]{suffix} ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not raw or raw.lower() in CANCEL_KEYWORDS:
        return None

    return raw


def pause(message: str = "Press ENTER to continue...") -> None:
    """Simple pause helper so the user can read output before continuing."""
    try:
        input(f"\n{message}")
    except (EOFError, KeyboardInterrupt):
        pass


def sanitize_filename(name: str) -> str:
    """Remove characters that are illegal in Windows filenames."""
    illegal = '<>:"/\\|?*'
    for ch in illegal:
        name = name.replace(ch, "")
    return name.strip()


def is_frozen() -> bool:
    """Return True if running from a PyInstaller-built executable."""
    return getattr(sys, "frozen", False)
