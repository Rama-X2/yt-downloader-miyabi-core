"""
splash.py
---------
Displays the startup splash screen: the green ASCII logo, app/version
information, and results of environment checks (yt-dlp, ffmpeg, aria2).

Single responsibility: startup presentation + environment verification
gate before the main menu is shown.
"""

from __future__ import annotations

import time
from typing import Any

from rich.align import Align
from rich.table import Table

from Source import banner
from Source.utils import check_environment, clear_screen, console


def _status_row(table: Table, label: str, ok: bool, detail: str) -> None:
    style = "success" if ok else "error"
    symbol = "✔" if ok else "✘"
    table.add_row(label, f"[{style}]{symbol} {detail}[/{style}]")


def show_splash(config: dict[str, Any]) -> dict[str, Any]:
    """
    Render the splash screen and perform startup checks.

    Returns the environment dictionary produced by check_environment(),
    so the caller (menu.py) can decide whether to warn the user about
    missing components before continuing.
    """
    clear_screen()
    banner.render_logo(console)

    app_info = config.get("app", {})
    console.print()
    banner.render_footer(
        console,
        f"{app_info.get('name', 'YouTube Downloader')}  |  "
        f"Version {app_info.get('version', '1.0.0')}",
    )
    console.print()

    with console.status("[primary]Running startup checks...[/primary]", spinner="dots"):
        time.sleep(0.6)  # brief pause purely for a polished startup feel
        env = check_environment(config)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Component", style="secondary", width=22)
    table.add_column("Status")

    _status_row(
        table,
        "yt-dlp (Python API)",
        env["yt_dlp_api"],
        f"v{env['yt_dlp_version']}" if env["yt_dlp_api"] else "Not installed",
    )
    _status_row(
        table,
        "FFmpeg",
        env["ffmpeg_path"] is not None,
        "Detected" if env["ffmpeg_path"] else "Not found",
    )
    _status_row(
        table,
        "aria2c",
        env["aria2c_path"] is not None,
        "Detected" if env["aria2c_path"] else "Not found (optional)",
    )

    console.print(Align.center(table))
    console.print()

    if not env["yt_dlp_api"]:
        console.print(
            "[error]Critical:[/error] yt-dlp Python package is not installed. "
            "Install it with: [secondary]pip install yt-dlp[/secondary]"
        )
    if not env["ffmpeg_path"]:
        console.print(
            "[warning]Warning:[/warning] FFmpeg was not found. Merging video/audio "
            "and MP3 conversion will not work until FFmpeg is available."
        )
    if not env["aria2c_path"]:
        console.print(
            "[warning]Notice:[/warning] aria2c was not found. Downloads will use "
            "yt-dlp's native downloader instead of aria2."
        )

    console.print()
    time.sleep(0.8)
    return env
