import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from podcast2zim.feed import EpisodeData, PodcastData
from podcast2zim.scraper import DEFAULT_COVER_PATH, Podcast2Zim

NOW = datetime.datetime.now(datetime.timezone.utc)


# Tests for validate_dateafter_input()
@pytest.fixture
def scraper():
    """Creates a raw instance of Podcast2Zim without trigerring the __init__"""
    instance = Podcast2Zim.__new__(Podcast2Zim)
    instance.dateafter_datetime = None
    return instance


def test_validate_dateafter_input_none(scraper: Podcast2Zim):
    scraper.dateafter = None
    scraper.validate_dateafter_input()

    assert scraper.dateafter_datetime is None


def test_validate_dateafter_input_errors_on_invalid_date_format(scraper: Podcast2Zim):
    scraper.dateafter = "20992321"

    with pytest.raises(ValueError, match="Invalid dateafter input"):
        scraper.validate_dateafter_input()


def test_validate_dateafter_input_valid_past_date(scraper: Podcast2Zim):
    scraper.dateafter = "20240321"
    scraper.validate_dateafter_input()

    expected = datetime.datetime(2024, 3, 21, tzinfo=datetime.timezone.utc)

    assert scraper.dateafter_datetime == expected


def test_validate_dateafter_input_errors_on_valid_future_date(scraper: Podcast2Zim):
    scraper.dateafter = "20990321"

    with pytest.raises(ValueError, match="cannot be a future date"):
        scraper.validate_dateafter_input()


# Tests for extract_episodes_list()
@pytest.fixture
def scraper_with_episodes():
    """Creates a raw instance of Podcast2Zim without trigerring the __init__"""
    instance = Podcast2Zim.__new__(Podcast2Zim)
    instance.max_episodes = None
    instance.dateafter_datetime = None

    audio_url = "https://nihongo.com"
    audio_mimetype = "audio/mpeg"

    oldest_episode = EpisodeData(
        id="oldest-ep",
        title="on happenings last year",
        summary="old",
        duration=1200,
        published=NOW - datetime.timedelta(days=365),
        audio_url=audio_url,
        audio_mimetype=audio_mimetype,
    )

    middle_episode = EpisodeData(
        id="middle-ep",
        title="happenings a month ago",
        summary="fresh",
        duration=1200,
        published=NOW - datetime.timedelta(days=30),
        audio_url=audio_url,
        audio_mimetype=audio_mimetype,
    )

    newest_episode = EpisodeData(
        id="newest-ep",
        title="on happenings today",
        summary="fresh",
        duration=1200,
        published=NOW,
        audio_url=audio_url,
        audio_mimetype=audio_mimetype,
    )

    dateless_episode = EpisodeData(
        id="dateless-ep",
        title="on forgotten matters",
        summary="dateless",
        duration=1200,
        published=None,
        audio_url=audio_url,
        audio_mimetype=audio_mimetype,
    )

    instance.podcast_data = PodcastData(
        title="Mock Podcast",
        summary="mock this",
        author="genos",
        language="eng",
        artwork_url="nothing to see here",
        episodes=[newest_episode, middle_episode, oldest_episode, dateless_episode],
    )
    return instance


def test_extract_episodes_list_returns_all_episodes_if_no_filters(
    scraper_with_episodes: Podcast2Zim,
):
    scraper_with_episodes.extract_episodes_list()

    assert len(scraper_with_episodes.podcast_data.episodes) == 4
    assert scraper_with_episodes.podcast_data.episodes[0].id == "newest-ep"
    assert scraper_with_episodes.podcast_data.episodes[1].id == "middle-ep"
    assert scraper_with_episodes.podcast_data.episodes[2].id == "oldest-ep"
    assert scraper_with_episodes.podcast_data.episodes[3].id == "dateless-ep"


def test_extract_episodes_list_returns_all_episodes_with_dateafter_filter(
    scraper_with_episodes: Podcast2Zim,
):
    scraper_with_episodes.dateafter_datetime = NOW - datetime.timedelta(days=40)
    scraper_with_episodes.extract_episodes_list()

    assert len(scraper_with_episodes.podcast_data.episodes) == 2
    assert scraper_with_episodes.podcast_data.episodes[0].id == "newest-ep"
    assert scraper_with_episodes.podcast_data.episodes[1].id == "middle-ep"


def test_extract_episodes_list_returns_n_episodes_with_max_episodes_filter(
    scraper_with_episodes: Podcast2Zim,
):
    scraper_with_episodes.max_episodes = 3
    scraper_with_episodes.extract_episodes_list()

    assert len(scraper_with_episodes.podcast_data.episodes) == 3
    assert scraper_with_episodes.podcast_data.episodes[0].id == "newest-ep"
    assert scraper_with_episodes.podcast_data.episodes[1].id == "middle-ep"
    assert scraper_with_episodes.podcast_data.episodes[2].id == "oldest-ep"


def test_extract_episodes_list_returns_n_episodes_with_max_episodes_filter_as_zero(
    scraper_with_episodes: Podcast2Zim,
):
    scraper_with_episodes.max_episodes = 0
    scraper_with_episodes.extract_episodes_list()

    assert len(scraper_with_episodes.podcast_data.episodes) == 4


def test_extract_episodes_list_returns_n_episodes_with_both_filters(
    scraper_with_episodes: Podcast2Zim,
):
    scraper_with_episodes.max_episodes = 3
    scraper_with_episodes.dateafter_datetime = NOW - datetime.timedelta(days=10)
    scraper_with_episodes.extract_episodes_list()

    assert len(scraper_with_episodes.podcast_data.episodes) == 1


# Tests for update_metadata()
@pytest.fixture
def scraper_with_metadata(tmp_path: Path):
    """Creates a raw instance of Podcast2Zim without trigerring the __init__"""
    instance = Podcast2Zim.__new__(Podcast2Zim)
    instance.title = ""
    instance.description = ""
    instance.long_description = ""
    instance.creator = None
    instance.tags = []
    instance._cover_ext = ".jpg"
    instance.build_dir = tmp_path / "mock_build_dir"
    instance.main_color = None
    instance.secondary_color = None

    episode = EpisodeData(
        id="ep",
        title="mock episode",
        summary="mock this",
        duration=1200,
        published=None,
        audio_url="https://mock.com",
        audio_mimetype="audio/mpeg",
    )

    instance.podcast_data = PodcastData(
        title="mock podcast",
        summary="mock this",
        author="genos",
        language="eng",
        artwork_url="nothing to see here",
        episodes=[episode],
    )
    return instance


def fake_convert(src, dst):
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.touch()


def test_update_metadata_correctly_uses_defaults(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mocker.patch("podcast2zim.scraper.stream_file")
    mocker.patch("podcast2zim.scraper.resize_image")
    mocker.patch("podcast2zim.scraper.get_colors", return_value=("#AAAAAA", "#BBBBBB"))
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)

    scraper_with_metadata.update_metadata()

    assert scraper_with_metadata.title == "mock podcast"
    assert scraper_with_metadata.description == "mock this"
    assert scraper_with_metadata.creator == "genos"
    assert "podcast" in scraper_with_metadata.tags
    assert "_audios:yes" in scraper_with_metadata.tags
    assert scraper_with_metadata.main_color == "#AAAAAA"
    assert scraper_with_metadata.secondary_color == "#BBBBBB"


def test_update_metadata_downloads_artwork_when_available(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mock_stream = mocker.patch("podcast2zim.scraper.stream_file")
    mocker.patch("podcast2zim.scraper.resize_image")
    mocker.patch("podcast2zim.scraper.get_colors", return_value=("#AAAAAA", "#BBBBBB"))
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)

    scraper_with_metadata.update_metadata()

    mock_stream.assert_called_once()


def test_update_metadata_uses_default_image_when_artwork_unavailable(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mock_stream_file = mocker.patch("podcast2zim.scraper.stream_file")
    mocker.patch("podcast2zim.scraper.resize_image")
    mocker.patch("podcast2zim.scraper.get_colors", return_value=("#AAAAAA", "#BBBBBB"))
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)
    mock_shutil_copy = mocker.patch("podcast2zim.scraper.shutil.copy")

    scraper_with_metadata.podcast_data.artwork_url = None

    scraper_with_metadata.update_metadata()

    mock_stream_file.assert_not_called()
    mock_shutil_copy.assert_called_once_with(
        DEFAULT_COVER_PATH, scraper_with_metadata.cover_path
    )


def test_update_metadata_skips_download_when_cover_image_exists(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mock_stream_file = mocker.patch("podcast2zim.scraper.stream_file")
    mock_shutil_copy = mocker.patch("podcast2zim.scraper.shutil.copy")
    mocker.patch("podcast2zim.scraper.resize_image")
    mocker.patch("podcast2zim.scraper.get_colors", return_value=("#AAAAAA", "#BBBBBB"))
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)

    scraper_with_metadata.cover_path.parent.mkdir(parents=True, exist_ok=True)
    scraper_with_metadata.cover_path.touch()

    scraper_with_metadata.update_metadata()

    mock_stream_file.assert_not_called()
    mock_shutil_copy.assert_not_called()


def test_update_metadata_skips_color_extraction_when_colors_provided(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mocker.patch("podcast2zim.scraper.stream_file")
    mocker.patch("podcast2zim.scraper.resize_image")
    mock_get_colors = mocker.patch("podcast2zim.scraper.get_colors")
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)

    scraper_with_metadata.main_color = "#111111"
    scraper_with_metadata.secondary_color = "#222222"

    scraper_with_metadata.update_metadata()

    mock_get_colors.assert_not_called()
    assert scraper_with_metadata.main_color == "#111111"
    assert scraper_with_metadata.secondary_color == "#222222"


def test_update_metadata_creator_falls_back_to_podcast_title(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mocker.patch("podcast2zim.scraper.stream_file")
    mocker.patch("podcast2zim.scraper.resize_image")
    mocker.patch("podcast2zim.scraper.get_colors", return_value=("#AAAAAA", "#BBBBBB"))
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)

    scraper_with_metadata.podcast_data.author = ""
    scraper_with_metadata.podcast_data.title = "fallback title"
    scraper_with_metadata.creator = None

    scraper_with_metadata.update_metadata()

    assert scraper_with_metadata.creator == "fallback title"


def test_update_metadata_prevents_duplicate_audio_tag(
    scraper_with_metadata: Podcast2Zim, mocker: MockerFixture
):
    mocker.patch("podcast2zim.scraper.stream_file")
    mocker.patch("podcast2zim.scraper.resize_image")
    mocker.patch("podcast2zim.scraper.get_colors", return_value=("#AAAAAA", "#BBBBBB"))
    mocker.patch("podcast2zim.scraper.convert_image", side_effect=fake_convert)

    scraper_with_metadata.tags = ["_audios:yes", "custom_tag"]

    scraper_with_metadata.update_metadata()

    assert len(scraper_with_metadata.tags) == 2
    assert scraper_with_metadata.tags.count("_audios:yes") == 1


# Tests for ep audio/thumbnail download (Gemini was used from here)
@pytest.fixture
def dummy_episode():
    return EpisodeData(
        id="dummy-ep",
        title="dummy episode",
        summary="dummy this",
        duration=1200,
        published=None,
        audio_url="https://mock.com/audio.mp3",
        audio_mimetype="audio/mpeg",
        thumbnail_url="https://mock.com/thumb.png",
    )


@pytest.fixture
def scraper_for_downloads(tmp_path: Path):
    """Provides a scraper with mocked ZIM and filesystem for download tests"""
    instance = Podcast2Zim.__new__(Podcast2Zim)
    instance.build_dir = tmp_path / "mock_build_dir"
    instance.build_dir.mkdir(parents=True)

    # Must explicitly mock the Kiwix Creator to avoid C++ binding crashes
    instance.zim_file = MagicMock()
    instance.audios_zim_path = {}
    instance.s3_storage = None
    return instance


def test_download_ep_audio_returns_false_on_download_error(
    scraper_for_downloads: Podcast2Zim,
    dummy_episode: EpisodeData,
    mocker: MockerFixture,
):
    mock_download = mocker.patch(
        "podcast2zim.scraper.download_file", side_effect=Exception("Network timeout")
    )
    mock_add_file = mocker.patch.object(scraper_for_downloads, "add_file_to_zim")

    result = scraper_for_downloads.download_ep_audio(
        dummy_episode, progress=MagicMock()
    )

    assert result is False
    mock_download.assert_called_once()
    mock_add_file.assert_not_called()


def test_download_ep_audio_intercepts_via_cache_and_skips_download(
    scraper_for_downloads: Podcast2Zim,
    dummy_episode: EpisodeData,
    mocker: MockerFixture,
):
    scraper_for_downloads.s3_storage = MagicMock()
    mock_download_cache = mocker.patch.object(
        scraper_for_downloads, "download_from_cache", return_value=True
    )
    mock_download_file = mocker.patch("podcast2zim.scraper.download_file")
    mock_add_file = mocker.patch.object(scraper_for_downloads, "add_file_to_zim")

    result = scraper_for_downloads.download_ep_audio(
        dummy_episode, progress=MagicMock()
    )

    assert result is True
    mock_download_cache.assert_called_once()
    mock_download_file.assert_not_called()
    mock_add_file.assert_called_once()


def test_download_ep_thumbnail_returns_false_on_download_error(
    scraper_for_downloads: Podcast2Zim,
    dummy_episode: EpisodeData,
    mocker: MockerFixture,
):
    mock_download = mocker.patch(
        "podcast2zim.scraper.download_file", side_effect=Exception("404 Not Found")
    )
    mock_convert = mocker.patch("podcast2zim.scraper.convert_image")

    result = scraper_for_downloads.download_ep_thumbnail(
        dummy_episode, progress=MagicMock()
    )

    assert result is False
    mock_download.assert_called_once()
    mock_convert.assert_not_called()


def test_download_ep_thumbnail_returns_false_on_conversion_error(
    scraper_for_downloads: Podcast2Zim,
    dummy_episode: EpisodeData,
    mocker: MockerFixture,
):
    # The download succeeds, but the conversion to webp fails
    mocker.patch("podcast2zim.scraper.download_file")
    mock_convert = mocker.patch(
        "podcast2zim.scraper.convert_image", side_effect=Exception("Corrupt image data")
    )
    mock_add_file = mocker.patch.object(scraper_for_downloads, "add_file_to_zim")

    result = scraper_for_downloads.download_ep_thumbnail(
        dummy_episode, progress=MagicMock()
    )

    assert result is False
    mock_convert.assert_called_once()
    mock_add_file.assert_not_called()


def test_batch_download_succeeds_even_if_thumbnail_fails(
    scraper_for_downloads: Podcast2Zim,
    dummy_episode: EpisodeData,
    mocker: MockerFixture,
):
    scraper_for_downloads.episodes_processed = 0
    scraper_for_downloads.episodes_count = 1
    scraper_for_downloads._progress_lock = MagicMock()

    # Audio succeeds, but thumbnail fails
    mocker.patch.object(scraper_for_downloads, "download_ep_audio", return_value=True)
    mocker.patch.object(
        scraper_for_downloads, "download_ep_thumbnail", return_value=False
    )

    succeeded, failed = scraper_for_downloads.download_episode_files_batch(
        [dummy_episode], progress=MagicMock()
    )

    assert dummy_episode.id in succeeded
    assert dummy_episode.id not in failed
