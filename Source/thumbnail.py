"""
thumbnail.py
------------
Downloads the highest-resolution thumbnail available for a YouTube video.

Single responsibility: thumbnail discovery + download. Uses the `requests`
library for the actual HTTP transfer (metadata still comes from yt-dlp).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import requests

from Source.downloader import DownloaderError, fetch_metadata, print_metadata_summary
from Source.utils import console, get_logger, pause, prompt_input, sanitize_filename


def get_best_thumbnail(info: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Return the thumbnail entry with the largest resolution (width * height).
    Falls back to the last entry in the `thumbnails` list, or the plain
    `thumbnail` URL field, if resolution data is unavailable.
    """
    thumbnails = info.get("thumbnails") or []
    if not thumbnails:
        url = info.get("thumbnail")
        return {"url": url} if url else None

    def area(thumb: dict[str, Any]) -> int:
        width = thumb.get("width") or 0
        height = thumb.get("height") or 0
        return width * height

    with_dimensions = [t for t in thumbnails if t.get("width") and t.get("height")]
    if with_dimensions:
        return max(with_dimensions, key=area)

    # No resolution metadata at all: assume the list is ordered worst -> best
    return thumbnails[-1]


def download_thumbnail_file(url: str, destination_dir: Path, base_name: str) -> str:
    """Download the thumbnail image at `url` into destination_dir."""
    destination_dir.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    ext = "jpg"
    if "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"
    elif "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"

    safe_name = sanitize_filename(base_name) or "thumbnail"
    file_path = destination_dir / f"{safe_name}.{ext}"

    with open(file_path, "wb") as fh:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                fh.write(chunk)

    return str(file_path)


def run_thumbnail_download_flow(config: dict[str, Any], env: dict[str, Any]) -> None:
    """Full interactive workflow for 'Download Thumbnail'."""
    logger = get_logger(config)

    url = prompt_input("Paste YouTube URL >")
    if url is None:
        console.print("[secondary]Dibatalkan. Kembali ke menu utama.[/secondary]")
        return

    try:
        with console.status("[primary]Fetching metadata...[/primary]", spinner="dots"):
            info = fetch_metadata(url)
    except DownloaderError as exc:
        console.print(f"[error]{exc}[/error]")
        logger.error(str(exc))
        pause()
        return

    console.print()
    print_metadata_summary(info)
    console.print()

    best_thumb = get_best_thumbnail(info)
    if not best_thumb or not best_thumb.get("url"):
        console.print("[error]No thumbnail found for this video.[/error]")
        pause()
        return

    width = best_thumb.get("width")
    height = best_thumb.get("height")
    resolution_note = f"{width}x{height}" if width and height else "unknown resolution"
    console.print(f"[secondary]Best thumbnail found:[/secondary] {resolution_note}")

    try:
        downloads_dir = Path(config["paths"]["downloads_dir"])
        title = info.get("title", info.get("id", "thumbnail"))

        with console.status("[primary]Downloading thumbnail...[/primary]", spinner="dots"):
            file_path = download_thumbnail_file(best_thumb["url"], downloads_dir, title)

    except requests.exceptions.RequestException as exc:
        console.print(f"[error]Network error while downloading thumbnail: {exc}[/error]")
        logger.error("Thumbnail download failed: %s", exc)
        pause()
        return
    except (OSError, PermissionError) as exc:
        console.print(f"[error]File system error: {exc}[/error]")
        logger.error("File system error while saving thumbnail: %s", exc)
        pause()
        return

    console.print(f"\n[success]Thumbnail saved:[/success] {file_path}")
    logger.info("Thumbnail downloaded: %s", file_path)
    pause()
