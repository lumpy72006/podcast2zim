import logging
from pathlib import Path

from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.style import Style
from rich.theme import Theme

from podcast2zim.__about__ import __version__

ROOT_DIR = Path(__file__).parent
NAME = ROOT_DIR.name

SCRAPER = f"{NAME} {__version__}"

# strip colors from the progress bar
custom_theme = Theme(
    {
        "progress.description": Style(color="default"),
        "progress.percentage": Style(color="default"),
        "progress.remaining": Style(color="default"),
        "bar.complete": Style(color="#bbbbbb"),  # light grey
        "bar.finished": Style(color="#bbbbbb"),
        "bar.back": Style(color="#444444"),  # dark grey background
    }
)

console = Console(theme=custom_theme)

handler = RichHandler(
    console=console,
    show_time=False,
    show_level=False,
    show_path=False,
    enable_link_path=False,
    highlighter=NullHighlighter(),
)

logger = logging.getLogger(NAME)
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s::%(asctime)s] %(levelname)s:%(message)s",
    handlers=[handler],
)
