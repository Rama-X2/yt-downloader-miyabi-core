"""
banner.py
---------
ASCII art and branding elements for Miyabi Core.

This module has a single responsibility: rendering the visual identity
of the application (logo, header bars, section titles). It contains no
business logic.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Original ASCII wordmark - not copied from any third-party tool.
# Every row is padded to the exact same width (70 chars) so the letters
# stay aligned regardless of terminal font/width.
_LOGO = r"""
 ____      _    __  __    _      ____  _____ ______     _______ ____
|  _ \    / \  |  \/  |  / \    / ___|| ____|  _ \ \   / / ____|  _ \
| |_) |  / _ \ | |\/| | / _ \   \___ \|  _| | |_) \ \ / /|  _| | |_) |
|  _ <  / ___ \| |  | |/ ___ \   ___) | |___|  _ < \ V / | |___|  _ <
|_| \_\/_/   \_\_|  |_/_/   \_\ |____/|_____|_| \_\ \_/  |_____|_| \_\

MIYABI CORE // YOUTUBE DOWNLOADER
"""


def render_logo(console: Console) -> None:
    """Print the green ASCII logo, centered."""
    logo_text = Text(_LOGO, style="primary", justify="center")
    console.print(Align.center(logo_text))


def render_title_bar(console: Console, subtitle: str = "") -> None:
    """Print a compact title bar used at the top of menu screens."""
    title = Text("YouTube Downloader - Miyabi Core", style="primary")
    if subtitle:
        title.append(f"  •  {subtitle}", style="secondary")
    console.print(Panel(Align.center(title), border_style="primary", expand=True))


def render_section(console: Console, title: str) -> None:
    """Print a section header, e.g. '── Download Video ──'."""
    console.print()
    console.rule(f"[accent]{title}[/accent]", style="primary")


def render_footer(console: Console, text: str) -> None:
    """Print a muted footer line, e.g. version / copyright info."""
    console.print(Align.center(Text(text, style="muted")))
