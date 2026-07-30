"""
settings.py
-----------
Interactive settings menu that lets the user configure:
    * Download folder
    * Theme
    * Whether to use aria2
    * Concurrent fragments
    * Output format (merge_output_format for video)

Single responsibility: reading/updating config.json through a guided
terminal menu. Persistence itself is delegated to Source.utils.save_config.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.table import Table

from Source.utils import clear_screen, console, get_logger, pause, prompt_input, save_config
from Source import banner

_THEME_CHOICES = ["green", "blue", "purple", "red", "cyan"]
_VIDEO_FORMAT_CHOICES = ["mp4", "mkv", "webm"]


def _render_current_settings(config: dict[str, Any]) -> None:
    table = Table(title="Current Settings", header_style="primary")
    table.add_column("#", style="secondary", width=3, justify="center")
    table.add_column("Setting", style="secondary")
    table.add_column("Value", style="primary")

    dl = config["download"]
    table.add_row("1", "Download folder", config["paths"]["downloads_dir"])
    table.add_row("2", "Theme", config["theme"]["primary"])
    table.add_row("3", "Use aria2", "ON" if dl.get("use_aria2") else "OFF")
    table.add_row("4", "Concurrent fragments", str(dl.get("concurrent_fragments")))
    table.add_row("5", "Output format (video merge)", dl.get("merge_output_format"))
    table.add_row("0", "Back to main menu", "")

    console.print(table)


def _set_download_folder(config: dict[str, Any]) -> bool:
    new_path = prompt_input("\nEnter new download folder path >")
    if new_path is None:
        return False

    try:
        Path(new_path).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        console.print(f"[error]Could not create/access that folder: {exc}[/error]")
        pause()
        return False

    config["paths"]["downloads_dir"] = new_path
    console.print(f"[success]Download folder updated to:[/success] {new_path}")
    return True


def _set_theme(config: dict[str, Any]) -> bool:
    console.print()
    for idx, theme_name in enumerate(_THEME_CHOICES, start=1):
        console.print(f"[primary][{idx}][/primary] {theme_name}")

    choice = prompt_input("\nChoose theme >")
    if choice is None or not choice.isdigit() or not (1 <= int(choice) <= len(_THEME_CHOICES)):
        return False

    selected = _THEME_CHOICES[int(choice) - 1]
    config["theme"]["primary"] = selected
    console.print(
        f"[success]Theme updated to '{selected}'.[/success] "
        "[muted](Restart the app to fully apply new accent colors.)[/muted]"
    )
    return True


def _toggle_aria2(config: dict[str, Any]) -> bool:
    current = config["download"].get("use_aria2", True)
    config["download"]["use_aria2"] = not current
    state = "ON" if config["download"]["use_aria2"] else "OFF"
    console.print(f"[success]aria2 usage set to {state}.[/success]")
    return True


def _set_concurrent_fragments(config: dict[str, Any]) -> bool:
    value = prompt_input("\nEnter number of concurrent fragments (1-32) >")
    if value is None or not value.isdigit() or not (1 <= int(value) <= 32):
        return False

    config["download"]["concurrent_fragments"] = int(value)
    console.print(f"[success]Concurrent fragments set to {value}.[/success]")
    return True


def _set_output_format(config: dict[str, Any]) -> bool:
    console.print()
    for idx, fmt in enumerate(_VIDEO_FORMAT_CHOICES, start=1):
        console.print(f"[primary][{idx}][/primary] {fmt}")

    choice = prompt_input("\nChoose output format >")
    if choice is None or not choice.isdigit() or not (1 <= int(choice) <= len(_VIDEO_FORMAT_CHOICES)):
        return False

    selected = _VIDEO_FORMAT_CHOICES[int(choice) - 1]
    config["download"]["merge_output_format"] = selected
    console.print(f"[success]Output format updated to '{selected}'.[/success]")
    return True


def run_settings_menu(config: dict[str, Any]) -> None:
    """Main loop for the Settings screen. Mutates and saves `config` in place."""
    logger = get_logger(config)

    while True:
        clear_screen()
        banner.render_title_bar(console, "Settings")
        console.print()
        _render_current_settings(config)

        choice = prompt_input("\nSelect option >", hint=False)
        if choice is None or choice == "0":
            save_config(config)
            logger.info("Settings saved.")
            return

        handlers = {
            "1": _set_download_folder,
            "2": _set_theme,
            "3": _toggle_aria2,
            "4": _set_concurrent_fragments,
            "5": _set_output_format,
        }

        handler = handlers.get(choice)
        if handler is None:
            # Any unrecognized option quietly returns to the settings screen.
            continue

        changed = handler(config)
        if changed:
            save_config(config)
            pause()
