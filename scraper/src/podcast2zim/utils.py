import hashlib
import os
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

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
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


def clean_summary(text: str) -> str:
    """Strip HTML tags from feed-sourced text"""
    return BeautifulSoup(text, "html.parser").get_text().strip()


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
    progress: Progress | None,
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

    headers = headers or DEFAULT_HEADERS

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


def create_episode_id(id: str) -> str:
    """create a filesystem and ZIM-path safe episode id"""
    return hashlib.sha1(id.encode("utf-8")).hexdigest()[:16]
