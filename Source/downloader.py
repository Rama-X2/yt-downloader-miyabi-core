"""
downloader.py
-------------
Handles fetching video metadata and downloading video/audio streams.

Single responsibility: everything related to talking to yt-dlp's Python
API, presenting format tables, and orchestrating downloads that use
external aria2 (as the fragment downloader) and external FFmpeg (as the
merge/remux/convert engine).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from Source.utils import (
    console,
    format_bytes,
    format_duration,
    format_upload_date,
    get_logger,
    pause,
    prompt_input,
)


class DownloaderError(Exception):
    """Raised for any recoverable downloader-related failure."""


# --------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------

def fetch_metadata(url: str) -> dict[str, Any]:
    """
    Fetch metadata for a YouTube URL using the yt-dlp Python API,
    without downloading any media (extract_flat / skip_download-like
    behaviour is achieved via download=False).
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloaderError(f"Could not fetch video info: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as-is
        raise DownloaderError(f"Unexpected error while fetching metadata: {exc}") from exc

    if info is None:
        raise DownloaderError("yt-dlp returned no information for this URL.")

    return info


def print_metadata_summary(info: dict[str, Any]) -> None:
    """Print title / channel / duration / upload date for the fetched video."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="secondary", width=14)
    table.add_column("Value", style="primary")

    table.add_row("Title", info.get("title", "Unknown"))
    table.add_row("Channel", info.get("uploader") or info.get("channel", "Unknown"))
    table.add_row("Duration", format_duration(info.get("duration")))
    table.add_row("Upload Date", format_upload_date(info.get("upload_date")))

    console.print(table)


# --------------------------------------------------------------------------
# Format tables
# --------------------------------------------------------------------------

def _is_video_format(fmt: dict[str, Any]) -> bool:
    return fmt.get("vcodec") not in (None, "none")


def _is_audio_only_format(fmt: dict[str, Any]) -> bool:
    return fmt.get("vcodec") in (None, "none") and fmt.get("acodec") not in (None, "none")


def get_video_formats(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Return formats that contain a video stream, best-first."""
    formats = info.get("formats") or []
    video_formats = [f for f in formats if _is_video_format(f)]
    video_formats.sort(
        key=lambda f: (f.get("height") or 0, f.get("fps") or 0, f.get("tbr") or 0),
        reverse=True,
    )
    return video_formats


def get_audio_formats(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Return audio-only formats, best-first by bitrate."""
    formats = info.get("formats") or []
    audio_formats = [f for f in formats if _is_audio_only_format(f)]
    audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    return audio_formats


def render_video_format_table(formats: list[dict[str, Any]]) -> None:
    table = Table(title="Available Video Formats", header_style="primary")
    table.add_column("ID", style="secondary", justify="center")
    table.add_column("Resolution", justify="center")
    table.add_column("Codec", justify="center")
    table.add_column("FPS", justify="center")
    table.add_column("Size", justify="right")

    for fmt in formats:
        height = fmt.get("height")
        width = fmt.get("width")
        resolution = f"{height}p" if height else "Unknown"
        fps = fmt.get("fps")
        if fps and height:
            resolution = f"{height}p{int(fps)}" if fps not in (25, 24, 23.976) else f"{height}p"

        codec = (fmt.get("vcodec") or "unknown").split(".")[0].upper()
        size = fmt.get("filesize") or fmt.get("filesize_approx")

        table.add_row(
            str(fmt.get("format_id", "?")),
            resolution,
            codec,
            str(int(fps)) if fps else "N/A",
            format_bytes(size),
        )

    console.print(table)


def render_audio_format_table(formats: list[dict[str, Any]]) -> None:
    table = Table(title="Available Audio Formats", header_style="primary")
    table.add_column("ID", style="secondary", justify="center")
    table.add_column("Codec", justify="center")
    table.add_column("Bitrate", justify="center")
    table.add_column("Size", justify="right")

    for fmt in formats:
        codec = (fmt.get("acodec") or "unknown").split(".")[0].upper()
        abr = fmt.get("abr")
        bitrate = f"{int(abr)} kbps" if abr else "Unknown"
        size = fmt.get("filesize") or fmt.get("filesize_approx")

        table.add_row(
            str(fmt.get("format_id", "?")),
            codec,
            bitrate,
            format_bytes(size),
        )

    console.print(table)


def find_format_by_id(formats: list[dict[str, Any]], format_id: str) -> Optional[dict[str, Any]]:
    for fmt in formats:
        if str(fmt.get("format_id")) == str(format_id):
            return fmt
    return None


# --------------------------------------------------------------------------
# Progress hook (bridges yt-dlp callbacks into a Rich Progress bar)
# --------------------------------------------------------------------------

class _RichProgressHook:
    """Stateful progress hook object passed to yt-dlp's progress_hooks."""

    def __init__(self) -> None:
        self.progress = Progress(
            TextColumn("[secondary]{task.fields[filename]}[/secondary]"),
            BarColumn(bar_width=None, style="primary", complete_style="success"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        self.task_ids: dict[str, int] = {}
        self.started = False

    def __enter__(self):
        self.progress.start()
        self.started = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.started:
            self.progress.stop()

    def hook(self, d: dict[str, Any]) -> None:
        filename = Path(d.get("filename", "download")).name
        key = d.get("info_dict", {}).get("format_id", filename) if isinstance(d.get("info_dict"), dict) else filename

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0

            if key not in self.task_ids:
                self.task_ids[key] = self.progress.add_task(
                    "download", filename=filename, total=total or None
                )

            task_id = self.task_ids[key]
            if total:
                self.progress.update(task_id, completed=downloaded, total=total)
            else:
                self.progress.update(task_id, completed=downloaded)

        elif d["status"] == "finished":
            if key in self.task_ids:
                task_id = self.task_ids[key]
                self.progress.update(task_id, completed=self.progress.tasks[task_id].total or 0)


# --------------------------------------------------------------------------
# Core download routine
# --------------------------------------------------------------------------

def _build_common_opts(config: dict[str, Any], env: dict[str, Any], hook: _RichProgressHook) -> dict[str, Any]:
    """Build the yt-dlp options shared by all download workflows."""
    paths = config["paths"]
    dl_settings = config["download"]

    downloads_dir = Path(paths.get("downloads_dir"))
    downloads_dir.mkdir(parents=True, exist_ok=True)

    outtmpl = str(downloads_dir / dl_settings.get("output_template", "%(title)s [%(id)s].%(ext)s"))

    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook.hook],
        "logger": _YdlLoggerAdapter(get_logger(config)),
        "concurrent_fragment_downloads": dl_settings.get("concurrent_fragments", 5),
    }

    ffmpeg_dir = env.get("ffmpeg_path")
    if ffmpeg_dir:
        opts["ffmpeg_location"] = str(Path(ffmpeg_dir).parent)

    if dl_settings.get("use_aria2") and env.get("aria2c_path"):
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = {
            "aria2c": [
                "--min-split-size=1M",
                f"--max-connection-per-server={dl_settings.get('aria2_max_connection_per_server', 16)}",
                f"--split={dl_settings.get('aria2_split', 16)}",
                "--summary-interval=1",
            ]
        }

    return opts


class _YdlLoggerAdapter:
    """Routes yt-dlp's internal log messages into our logging system."""

    def __init__(self, logger) -> None:
        self._logger = logger

    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            self._logger.debug(msg)
        else:
            self.info(msg)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)


def download_video(
    url: str,
    video_format_id: str,
    audio_format_id: str,
    config: dict[str, Any],
    env: dict[str, Any],
) -> str:
    """
    Download the chosen video+audio format combination, merging them with
    FFmpeg into a single file. Returns the resulting file path (best guess).
    """
    import yt_dlp

    logger = get_logger(config)
    merge_format = config["download"].get("merge_output_format", "mp4")

    with _RichProgressHook() as hook:
        opts = _build_common_opts(config, env, hook)
        opts["format"] = f"{video_format_id}+{audio_format_id}"
        opts["merge_output_format"] = merge_format

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            logger.error("Video download failed: %s", exc)
            raise DownloaderError(f"Download failed: {exc}") from exc

    filename = yt_dlp.YoutubeDL(opts).prepare_filename(result)
    logger.info("Video download completed: %s", filename)
    return filename


def download_audio(
    url: str,
    audio_format_id: str,
    config: dict[str, Any],
    env: dict[str, Any],
    convert_to_mp3: bool,
) -> str:
    """
    Download the chosen audio-only format. If convert_to_mp3 is True,
    FFmpeg (via yt-dlp's FFmpegExtractAudio postprocessor) converts it.
    """
    import yt_dlp

    logger = get_logger(config)

    with _RichProgressHook() as hook:
        opts = _build_common_opts(config, env, hook)
        opts["format"] = audio_format_id

        if convert_to_mp3:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": config["download"].get("audio_format", "mp3"),
                    "preferredquality": config["download"].get("audio_quality", "192"),
                }
            ]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            logger.error("Audio download failed: %s", exc)
            raise DownloaderError(f"Download failed: {exc}") from exc

    filename = yt_dlp.YoutubeDL(opts).prepare_filename(result)
    if convert_to_mp3:
        filename = str(Path(filename).with_suffix(f".{config['download'].get('audio_format', 'mp3')}"))
    logger.info("Audio download completed: %s", filename)
    return filename


# --------------------------------------------------------------------------
# Interactive workflow (called from menu.py)
# --------------------------------------------------------------------------

def run_video_download_flow(config: dict[str, Any], env: dict[str, Any]) -> None:
    """Full interactive workflow for 'Download Video'."""
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

    video_formats = get_video_formats(info)
    if not video_formats:
        console.print("[error]No video formats available for this video.[/error]")
        pause()
        return

    render_video_format_table(video_formats)
    video_id = prompt_input("\nVideo ID >")
    if video_id is None:
        console.print("[secondary]Dibatalkan. Kembali ke menu utama.[/secondary]")
        return
    selected_video = find_format_by_id(video_formats, video_id)
    if not selected_video:
        console.print(f"[error]Invalid Video ID: {video_id}[/error] [secondary](kembali ke menu)[/secondary]")
        pause()
        return

    audio_formats = get_audio_formats(info)
    if not audio_formats:
        console.print("[error]No audio-only formats available for this video.[/error]")
        pause()
        return

    console.print()
    render_audio_format_table(audio_formats)
    audio_id = prompt_input("\nAudio ID >")
    if audio_id is None:
        console.print("[secondary]Dibatalkan. Kembali ke menu utama.[/secondary]")
        return
    selected_audio = find_format_by_id(audio_formats, audio_id)
    if not selected_audio:
        console.print(f"[error]Invalid Audio ID: {audio_id}[/error] [secondary](kembali ke menu)[/secondary]")
        pause()
        return

    if not env.get("ffmpeg_path"):
        console.print(
            "[error]FFmpeg is required to merge video and audio, but it was not found.[/error]"
        )
        pause()
        return

    console.print(
        f"\n[secondary]Downloading video[/secondary] [primary]{video_id}[/primary] "
        f"[secondary]+ audio[/secondary] [primary]{audio_id}[/primary]...\n"
    )

    try:
        output_path = download_video(url, video_id, audio_id, config, env)
    except DownloaderError as exc:
        console.print(f"[error]{exc}[/error]")
        pause()
        return
    except (OSError, PermissionError) as exc:
        console.print(f"[error]File system error: {exc}[/error]")
        logger.error("File system error: %s", exc)
        pause()
        return

    console.print(f"\n[success]Download complete:[/success] {output_path}")
    pause()


def run_audio_download_flow(config: dict[str, Any], env: dict[str, Any]) -> None:
    """Full interactive workflow for 'Download Audio'."""
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

    audio_formats = get_audio_formats(info)
    if not audio_formats:
        console.print("[error]No audio-only formats available for this video.[/error]")
        pause()
        return

    render_audio_format_table(audio_formats)
    audio_id = prompt_input("\nAudio ID >")
    if audio_id is None:
        console.print("[secondary]Dibatalkan. Kembali ke menu utama.[/secondary]")
        return
    selected_audio = find_format_by_id(audio_formats, audio_id)
    if not selected_audio:
        console.print(f"[error]Invalid Audio ID: {audio_id}[/error] [secondary](kembali ke menu)[/secondary]")
        pause()
        return

    console.print(
        "\n[primary][1][/primary] Keep original audio format"
        "\n[primary][2][/primary] Convert to MP3 (requires FFmpeg)\n"
    )
    choice = prompt_input("Choice >")
    if choice is None:
        console.print("[secondary]Dibatalkan. Kembali ke menu utama.[/secondary]")
        return
    convert_to_mp3 = choice == "2"

    if convert_to_mp3 and not env.get("ffmpeg_path"):
        console.print(
            "[error]FFmpeg is required for MP3 conversion, but it was not found.[/error]"
        )
        pause()
        return

    console.print(f"\n[secondary]Downloading audio[/secondary] [primary]{audio_id}[/primary]...\n")

    try:
        output_path = download_audio(url, audio_id, config, env, convert_to_mp3)
    except DownloaderError as exc:
        console.print(f"[error]{exc}[/error]")
        pause()
        return
    except (OSError, PermissionError) as exc:
        console.print(f"[error]File system error: {exc}[/error]")
        logger.error("File system error: %s", exc)
        pause()
        return

    console.print(f"\n[success]Download complete:[/success] {output_path}")
    pause()
