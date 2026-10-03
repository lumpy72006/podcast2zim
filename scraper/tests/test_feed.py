import datetime
from unittest.mock import MagicMock

import pytest
import requests
from feedparser.util import FeedParserDict
from pytest_mock import MockerFixture

from podcast2zim.feed import (
    EpisodeData,
    FeedParseError,
    FeedResolutionError,
    PodcastData,
    _extract_episode,
    parse_feed,
    resolve_url,
)
from podcast2zim.utils import create_episode_id

APPLE_PODCASTS_URL = "https://podcasts.apple.com/us/podcast/the-daily/id1200361736"


@pytest.fixture
def mock_get(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("podcast2zim.feed.requests.get")


def create_mock_entry(**overrides) -> FeedParserDict:
    base_entry = {
        "id": "123456789",
        "title": "Genki",
        "links": [
            {
                "href": "https://example.com/audio.mp3",
                "type": "audio/mpeg",
                "rel": "enclosure",
            }
        ],
    }
    base_entry.update(overrides)
    return FeedParserDict(base_entry)


def test_resolve_url_passes_through_raw_feed(mock_get: MagicMock):
    raw_feed_url = "https://feeds.simplecast.com/Sl5CSM3S"
    result = resolve_url(raw_feed_url)

    assert result == raw_feed_url
    mock_get.assert_not_called()


def test_resolve_url_resolves_apple_podcast_url(mock_get: MagicMock):
    expected_feed_url = "https://feeds.simplecast.com/Sl5CSM3S"

    mock_get.return_value.json.return_value = {
        "results": [{"kind": "podcast", "feedUrl": expected_feed_url}]
    }

    result = resolve_url(APPLE_PODCASTS_URL)
    assert result == expected_feed_url
    mock_get.assert_called_once()


def test_resolve_url_raises_error_on_invalid_json(mock_get: MagicMock):
    mock_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
        "Expecting value", "", 0
    )

    with pytest.raises(
        FeedResolutionError, match="iTunes Lookup API returned invalid JSON"
    ):
        resolve_url(APPLE_PODCASTS_URL)


def test_resolve_url_raises_error_on_network_error(mock_get: MagicMock):
    mock_get.side_effect = requests.RequestException()

    with pytest.raises(FeedResolutionError, match="Network error"):
        resolve_url(APPLE_PODCASTS_URL)


def test_resolve_url_raises_error_if_not_podcast(mock_get: MagicMock):
    mock_get.return_value.json.return_value = {
        "results": [
            {"kind": "music", "feedUrl": "https://feeds.simplecast.com/Sl5CSM3S"}
        ]
    }

    with pytest.raises(FeedResolutionError, match="is 'music', not a podcast"):
        resolve_url(APPLE_PODCASTS_URL)


def test_resolve_url_raises_error_on_no_feed_url(mock_get: MagicMock):
    mock_get.return_value.json.return_value = {"results": [{"kind": "podcast"}]}

    with pytest.raises(FeedResolutionError, match="has no feedUrl"):
        resolve_url(APPLE_PODCASTS_URL)


################ parse feed tests
def test_parse_feed_raises_error_on_bozo_exception(mocker: MockerFixture):
    bozo_exception = "XML is broken"
    mock_parse = mocker.patch("podcast2zim.feed.feedparser.parse")
    mock_parse.return_value = FeedParserDict(
        {
            "bozo": True,
            "entries": [],
            "bozo_exception": bozo_exception,
        }
    )

    with pytest.raises(FeedParseError, match=bozo_exception):
        parse_feed("https://feeds.simplecast.com/Sl5CSM3S")


def test_parse_feed_ignores_bozo_exception_when_entries_present(mocker: MockerFixture):
    mock_parse = mocker.patch("podcast2zim.feed.feedparser.parse")
    mock_parse.return_value = FeedParserDict(
        {
            "bozo": True,
            "bozo_exception": "XML is broken",
            "feed": FeedParserDict(
                {
                    "title": "Nihongo con Teppei",
                    "summary": "This feed may not be well formed but still has entries.",
                }
            ),
            "entries": [create_mock_entry()],
        }
    )

    result = parse_feed("https://feeds.simplecast.com/Sl5CSM3S")

    assert isinstance(result, PodcastData)
    assert result.title == "Nihongo con Teppei"
    assert len(result.episodes) == 1
    assert result.episodes[0].title == "Genki"
    assert result.summary == "This feed may not be well formed but still has entries."


def test_parse_feed_handles_multiple_entries(mocker: MockerFixture):
    mock_parse = mocker.patch("podcast2zim.feed.feedparser.parse")
    mock_parse.return_value = FeedParserDict(
        {
            "bozo": False,
            "feed": FeedParserDict(
                {
                    "title": "Podcast with multiple entries",
                    "summary": "This podcast has 3 entries",
                }
            ),
            "entries": [
                create_mock_entry(id="ep-1", title="Episode 1"),
                create_mock_entry(id="ep-2", title="Episode 2"),
                create_mock_entry(id="ep-3", title="Episode 3"),
            ],
        }
    )

    result = parse_feed("https://feeds.simplecast.com/Sl5CSM3S")

    assert isinstance(result, PodcastData)

    assert len(result.episodes) == 3
    # verify order
    assert result.episodes[0].title == "Episode 1"
    assert result.episodes[0].id == create_episode_id("ep-1")

    assert result.episodes[1].title == "Episode 2"
    assert result.episodes[1].id == create_episode_id("ep-2")

    assert result.episodes[2].title == "Episode 3"
    assert result.episodes[2].id == create_episode_id("ep-3")


def test_extract_episode_returns_none_if_no_audio():
    entry = create_mock_entry(
        links=[
            {
                "href": "https://example.com/audio.mp3",
                "type": "video/mpeg",
                "rel": "enclosure",
            }
        ]
    )

    assert _extract_episode(entry) is None


def test_extract_episode_builds_full_episode_from_valid_entry():
    entry = create_mock_entry(published_parsed=(2026, 8, 9, 10, 0, 0, 6, 221, 0))

    result = _extract_episode(entry)

    assert isinstance(result, EpisodeData)
    assert result.id == create_episode_id("123456789")
    assert result.title == "Genki"
    assert result.audio_mimetype == "audio/mpeg"
    assert result.published == datetime.datetime(
        2026, 8, 9, 10, 0, 0, tzinfo=datetime.UTC
    )


def test_extract_episode_handles_missing_metadata_gracefully():
    entry = create_mock_entry(id=None, title=None)
    default_img_url = "https://example.com/fallback.jpg"

    result = _extract_episode(entry, default_img_url=default_img_url)

    assert isinstance(result, EpisodeData)
    assert result.id == create_episode_id("https://example.com/audio.mp3")
    assert result.title == "Untitled episode"
    assert result.summary == ""
    assert result.duration == 0
    assert result.published is None
    assert result.audio_mimetype == "audio/mpeg"
    assert result.thumbnail_url == default_img_url
