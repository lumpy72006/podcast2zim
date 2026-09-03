import logging
from pathlib import Path

from podcast2zim.__about__ import __version__

ROOT_DIR = Path(__file__).parent
NAME = ROOT_DIR.name

SCRAPER = f"{NAME} {__version__}"

logger = logging.getLogger(NAME)
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s::%(asctime)s] %(levelname)s:%(message)s",
)
