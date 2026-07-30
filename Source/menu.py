"""
menu.py
-------
Main menu loop for the application. Single responsibility: presenting the
menu, reading the user's choice, and dispatching to the relevant feature
module. Contains no download/settings/update business logic itself.
"""

from __future__ import annotations

from typing import Any

from Source import banner, downloader, settings, thumbnail, updater
from Source.utils import clear_screen, console, get_logger, pause, prompt_input


def _render_menu(env: dict[str, Any]) -> None:
    banner.render_title_bar(console, "Main Menu")
    console.print()
    console.print("  [primary][1][/primary] Download Video")
    console.print()
    console.print("  [primary][2][/primary] Download Audio")
    console.print()
    console.print("  [primary][3][/primary] Download Thumbnail")
    console.print()
    console.print("  [primary][4][/primary] Update yt-dlp")
    console.print()
    console.print("  [primary][5][/primary] Settings")
    console.print()
    console.print("  [primary][0][/primary] Exit")
    console.print()

    if not env.get("ffmpeg_path") or not env.get("aria2c_path"):
        missing = []
        if not env.get("ffmpeg_path"):
            missing.append("FFmpeg")
        if not env.get("aria2c_path"):
            missing.append("aria2")
        console.print(f"[warning]Notice: {', '.join(missing)} not detected.[/warning]\n")


def run_main_menu(config: dict[str, Any], env: dict[str, Any]) -> None:
    """
    Run the interactive main menu loop until the user chooses to exit.
    `env` is the environment-check dictionary produced at startup by
    Source.splash.show_splash(); it is refreshed after an update.
    """
    logger = get_logger(config)

    while True:
        clear_screen()
        banner.render_logo(console)
        console.print()
        _render_menu(env)

        choice = prompt_input("Select option >", hint=False)
        logger.info("Main menu selection: %s", choice)

        if choice in (None, "0"):
            console.print("\n[secondary]Goodbye![/secondary]")
            logger.info("Application exited by user.")
            break

        elif choice == "1":
            clear_screen()
            banner.render_section(console, "Download Video")
            downloader.run_video_download_flow(config, env)

        elif choice == "2":
            clear_screen()
            banner.render_section(console, "Download Audio")
            downloader.run_audio_download_flow(config, env)

        elif choice == "3":
            clear_screen()
            banner.render_section(console, "Download Thumbnail")
            thumbnail.run_thumbnail_download_flow(config, env)

        elif choice == "4":
            clear_screen()
            banner.render_section(console, "Update yt-dlp")
            updater.run_update_flow(config)
            # Refresh environment info in case the update changed the version.
            from Source.utils import check_environment

            env.update(check_environment(config))

        elif choice == "5":
            settings.run_settings_menu(config)

        else:
            console.print("[error]Invalid option. Please choose a valid menu item.[/error]")
            pause()
