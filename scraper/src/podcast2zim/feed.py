import datetime
import re
from dataclasses import dataclass, field

import feedparser
import requests
from feedparser.util import FeedParserDict

from podcast2zim.constants import logger
from podcast2zim.utils import clean_summary, normalize_duration

APPLE_PODCASTS_URL_RE = re.compile(r"podcasts\.apple\.com/.+/id(?P<apple_id>\d+)")
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"


class FeedError(Exception):
    """Base for any error that ends with no usable feed."""


class FeedResolutionError(FeedError):
    """Raised when a feed url can't be resolved to a usable RSS/Atom feed"""


class FeedParseError(FeedError):
    """Raised when a feed url can't be successfully parsed"""


@dataclass
class EpisodeData:
    id: str
    title: str
    summary: str
    duration: int
    published: datetime.datetime | None
    audio_url: str
    audio_mimetype: str | None
    thumbnail_url: str | None = None


@dataclass
class PodcastData:
    title: str
    summary: str
    author: str
    language: str
    artwork_url: str | None
    episodes: list[EpisodeData] = field(default_factory=list)


def resolve_url(feed_url: str) -> str:
    """Return a raw RSS/Atom feed URL, resolve first if Apple Podcast URL"""
    match = APPLE_PODCASTS_URL_RE.search(feed_url)

    if not match:
        logger.info("passing through as raw RSS/Atom URL")
        return feed_url

    apple_id = match.group("apple_id")
    logger.debug(f"Querying iTunes Lookup API for id: {apple_id}")

    try:
        response = requests.get(ITUNES_LOOKUP_URL, params={"id": apple_id}, timeout=30)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.JSONDecodeError as ex:
        raise FeedResolutionError(
            f"iTunes Lookup API returned invalid JSON for id {apple_id}: {ex}"
        ) from ex
    except requests.RequestException as ex:
        raise FeedResolutionError(
            f"Network error querying iTunes Lookup API for id {apple_id}: {ex}"
        ) from ex

    if not data.get("results"):
        raise FeedResolutionError(
            f"iTunes Lookup API returned no results for id {apple_id}"
        )

    kind = data["results"][0].get("kind")
    if kind != "podcast":
        raise FeedResolutionError(f"id: {apple_id} is {kind!r}, not a podcast")

    rss_url = data["results"][0].get("feedUrl")
    if not rss_url:
        raise FeedResolutionError(
            f"iTunes Lookup API result for id {apple_id} has no feedUrl "
            "(podcast may be Apple exclusive, no public RSS)"
        )

    logger.info(f"resolved {feed_url} to {rss_url}")
    return rss_url


def _extract_episode(
    entry: FeedParserDict, default_img_url: str | None = None
) -> EpisodeData | None:
    """Build an EpisodeData from a single feedparser entry, or None to skip
    it (e.g. no audio enclosure — can't build an episode without audio)."""
    enclosures = getattr(entry, "enclosures", [])
    audio_enclosure = next(
        (e for e in enclosures if e.get("type", "").startswith("audio")), None
    )

    if not audio_enclosure or not audio_enclosure.get("href"):
        logger.warning(
            f"Skipping episode with no audio enclosure: {getattr(entry, 'title', 'Untitled')}"
        )
        return None

    episode_id = getattr(entry, "id", None) or audio_enclosure["href"]
    published_parsed = getattr(entry, "published_parsed", None)
    published = (
        datetime.datetime(*published_parsed[:6], tzinfo=datetime.UTC)
        if published_parsed
        else None
    )

    return EpisodeData(
        id=episode_id,
        title=getattr(entry, "title", None) or "Untitled episode",
        summary=clean_summary(getattr(entry, "summary", "")),
        duration=normalize_duration(getattr(entry, "itunes_duration", None)),
        published=published,
        audio_url=audio_enclosure["href"],
        audio_mimetype=audio_enclosure.get("type"),
        thumbnail_url=getattr(getattr(entry, "image", None), "href", default_img_url),
    )


def parse_feed(feed_url: str) -> PodcastData:
    """Parse a resolved RSS/Atom feed URL into PodcastData + EpisodeData list."""

    logger.info("parsing feed...")
    podcast = feedparser.parse(feed_url)

    if podcast.bozo and not podcast.entries:
        # bozo==1 ==> "not strictly well-formed" but only bail if we can't get anything
        raise FeedParseError(
            f"Could not parse feed at {feed_url}: {getattr(podcast, 'bozo_exception', 'Unknown parsing error')}"
        )

    feed = podcast.feed
    default_img_url = getattr(getattr(feed, "image", None), "href", None)
    episodes = [
        ep
        for ep in (
            _extract_episode(entry, default_img_url) for entry in podcast.entries
        )
        if ep
    ]

    return PodcastData(
        title=getattr(feed, "title", "Untitled"),
        summary=clean_summary(getattr(feed, "summary", "")),
        author=getattr(feed, "author", ""),
        language=getattr(feed, "language", "en"),
        artwork_url=default_img_url,
        episodes=episodes,
    )
