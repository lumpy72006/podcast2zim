import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from rich.progress import Progress

AUDIO_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/aac": ".aac",
    "audio/wav": ".wav",
}


def guess_audio_ext(mimetype: str | None, url: str) -> str:
    """
    Prefer the feed's declard mimetype; fall back to the URL's suffix
    when mimetype is missing or not recognized
    """
    if mimetype and mimetype in AUDIO_EXTENSIONS:
        return AUDIO_EXTENSIONS[mimetype]

    url_ext = Path(urlparse(url).path).suffix
    return url_ext or ".mp3"


def split_into_paragraphs(text: str) -> list[str]:
    """Split feed-sourced text into paragraphs, collapsing noisy whitespace
    within each paragraph while preserving blank-line paragraph breaks."""
    # feed descriptions may have html tags so clean first
    cleaned_text = BeautifulSoup(text, "html.parser").get_text()

    paragraphs = re.split(r"\n\s*\n", cleaned_text)
    return [
        cleaned for para in paragraphs if (cleaned := re.sub(r"\s+", " ", para).strip())
    ]


def normalize_duration(raw: str | int | None) -> int:
    """normalize itunes_duration (HH:MM:SS, MM:SS, or raw seconds) to seconds.

    RSS feeds are inconsistent here — some give "1:02:33", some give a plain
    seconds string like "3753", some omit it entirely.
    """
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    parts = [int(p) for p in raw.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts[-3:]
    return hours * 3600 + minutes * 60 + seconds


def delete_callback(fpath: str | Path):
    """callback to delete file"""
    if Path(fpath).exists():
        os.unlink(fpath)


# Match stream_file logic and add custom download progress
from zimscraperlib.download import get_session


def download_file(
    url: str,
    filepath: Path,
    progress: Progress,
    task_id=None,
    block_size: int = 8192,
    proxies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    session: requests.Session | None = None,
    max_retries: int = 5,
    timeout: int = 10,
):
    """Downloads a file and safely updates a rich progress bar if provided."""
    if not session:
        session = get_session(max_retries)

    try:
        with session.get(
            url,
            stream=True,
            proxies=proxies,
            headers=headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()

            # dynamically set the total size one headers arrive
            if progress and task_id is not None:
                total_size = int(response.headers.get("content-length", 0))
                progress.update(task_id, total=total_size)

            with open(filepath, "wb") as file:
                for chunk in response.iter_content(chunk_size=block_size):
                    file.write(chunk)

                    # update the specific bar tied to this download
                    if progress and task_id is not None:
                        progress.update(task_id=task_id, advance=len(chunk))

    finally:
        # clear progress bar immediately
        if progress and task_id is not None:
            progress.remove_task(task_id)
