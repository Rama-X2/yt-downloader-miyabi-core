"""
updater.py
----------
Updates yt-dlp, either the standalone yt-dlp.exe binary (via its built-in
`-U` self-update flag) or the pip-installed `yt-dlp` Python package,
whichever is applicable in the current setup.

Single responsibility: running the update process and reporting results.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from Source.utils import console, get_logger, pause


def _update_standalone_binary(exe_path: str) -> tuple[bool, str]:
    """Run `yt-dlp.exe -U` and capture its output."""
    try:
        result = subprocess.run(
            [exe_path, "-U"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def _update_python_package() -> tuple[bool, str]:
    """Run `pip install --upgrade yt-dlp` using the current interpreter."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def run_update_flow(config: dict[str, Any]) -> None:
    """Interactive workflow for 'Update yt-dlp'."""
    logger = get_logger(config)
    console.print()

    exe_path = config["paths"].get("yt_dlp_exe", "")
    has_binary = exe_path and Path(exe_path).is_file()

    if has_binary:
        console.print(f"[secondary]Updating standalone binary:[/secondary] {exe_path}")
        with console.status("[primary]Running yt-dlp -U ...[/primary]", spinner="dots"):
            success, output = _update_standalone_binary(exe_path)
    else:
        console.print(
            "[secondary]No standalone yt-dlp.exe configured. "
            "Updating the Python package instead...[/secondary]"
        )
        with console.status("[primary]Running pip install --upgrade yt-dlp ...[/primary]", spinner="dots"):
            success, output = _update_python_package()

    console.print()
    if output:
        console.print(f"[muted]{output}[/muted]")

    if success:
        console.print("\n[success]yt-dlp update completed successfully.[/success]")
        logger.info("yt-dlp update completed successfully.")
    else:
        console.print("\n[error]yt-dlp update failed. See details above.[/error]")
        logger.error("yt-dlp update failed: %s", output)

    pause()
