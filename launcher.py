#!/usr/bin/env python3
"""
launcher.py
-----------
Entry point for the RAMA SERVER - MIYABI CORE YouTube Downloader.

Responsibilities:
    * Bootstrap configuration and logging.
    * Show the splash screen and run startup checks.
    * Hand control over to the main menu loop.
    * Catch and log any unhandled exception so the terminal window
      does not simply flash-close when compiled with PyInstaller.

This file intentionally contains no business logic - it only wires the
Source/ modules together.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Ensure the project root is importable whether run as a script or as a
# frozen PyInstaller executable.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Source import menu, splash
from Source.utils import console, ensure_directories, get_logger, load_config, pause


def main() -> int:
    config = load_config()
    ensure_directories(config)
    logger = get_logger(config)
    logger.info("Application starting.")

    try:
        env = splash.show_splash(config)
        pause("Press ENTER to continue to the main menu...")
        menu.run_main_menu(config, env)
    except KeyboardInterrupt:
        console.print("\n[warning]Interrupted by user. Exiting.[/warning]")
        logger.info("Application interrupted by user (Ctrl+C).")
        return 0
    except Exception as exc:  # noqa: BLE001 - top level safety net
        logger.error("Unhandled exception: %s", exc)
        logger.error(traceback.format_exc())
        console.print(f"\n[error]A fatal error occurred:[/error] {exc}")
        console.print("[muted]Details have been written to the Logs folder.[/muted]")
        pause("Press ENTER to close...")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
