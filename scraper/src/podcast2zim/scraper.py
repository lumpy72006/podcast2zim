import concurrent.futures
import datetime
import json
import re
import shutil
import tempfile
import threading
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse

import requests
from botocore import config
from kiwixstorage import KiwixStorage
from pif import get_public_ip
from zimscraperlib.download import stream_file
from zimscraperlib.image.conversion import convert_image
from zimscraperlib.image.presets import WebpHigh
from zimscraperlib.image.probing import get_colors, is_hex_color
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.inputs import compute_descriptions
from zimscraperlib.typing import Callback
from zimscraperlib.zim import Creator, metadata
from zimscraperlib.zim.filesystem import validate_file_creatable
from zimscraperlib.zim.indexing import IndexData

from podcast2zim.constants import SCRAPER, logger
from podcast2zim.feed import EpisodeData, parse_feed, resolve_url
from podcast2zim.schemas import Config, Episode, EpisodePreview, Podcast
from podcast2zim.utils import delete_callback, guess_audio_ext

DEFAULT_COVER_PATH = str(files("podcast2zim.assets") / "mic-svgrepo-com.png")


class Podcast2Zim:
    def __init__(
        self,
        feed_url: str,
        name: str,
        output_dir,
        fname: str,
        stats_filename: str,
        tmp_dir,
        zimui_dist,
        s3_url_with_credentials,
        use_any_optimized_version,
        max_concurrency,
        tags,
        language,
        publisher,
        title: str | None = None,
        creator: str | None = None,
        description: str | None = None,
        long_description: str | None = None,
        cover_image=None,
        main_color=None,
        secondary_color=None,
        max_episodes: int | None = None,
        dateafter: str | None = None,
    ):
        # options & zim params
        self.feed_url = feed_url
        self.name = name
        self.fname = fname
        self.tags = [t.strip() for t in tags.split(",") if t.strip()]
        self.title = title
        self.creator = creator
        self.publisher = publisher
        self.description = description
        self.long_description = long_description
        self.language = language
        self.cover_image = cover_image
        self.main_color = main_color
        self.secondary_color = secondary_color
        self.max_episodes = max_episodes
        self.dateafter = dateafter
        self.max_concurrency = max_concurrency
        self.dateafter_datetime = None

        # directory setup
        self.output_dir = Path(output_dir).expanduser().resolve()
        if tmp_dir:
            tmp_dir = Path(tmp_dir).expanduser().resolve()
            tmp_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir = Path(tempfile.mkdtemp(dir=tmp_dir))
        self.zimui_dist = Path(zimui_dist)

        # process-related
        self.episodes_processed = 0
        self.episodes_count = 0
        self.audios_zim_path = {}
        self._progress_lock = threading.Lock()

        # optimization cache
        self.s3_url_with_credentials = s3_url_with_credentials
        self.use_any_optimized_version = use_any_optimized_version
        self.s3_storage = None

        # scraper progress
        self.stats_path = None
        if stats_filename:
            self.stats_path = Path(stats_filename).expanduser()
            self.stats_path.parent.mkdir(parents=True, exist_ok=True)

        self._cover_ext = ".jpg"

    @property
    def episodes_dir(self):
        return self.build_dir.joinpath("episodes")

    @property
    def cover_path(self):
        return self.build_dir.joinpath(f"cover{self._cover_ext}")

    def run(self):
        try:
            # first report => creates a file with appropriate structure
            self.report_progress()

            self.validate_dateafter_input()

            if not self.name:
                raise Exception("name is mandatory")
            period = datetime.date.today().strftime("%Y-%m")
            self.fname = (
                self.fname.format(period=period)
                if self.fname
                else f"{self.name}_{period}.zim"
            )

            validate_file_creatable(self.output_dir, self.fname)

            if not self.build_dir.exists() or not self.build_dir.is_dir():
                raise OSError(f"Incorrect build_dir: {self.build_dir}")

            logger.info(f"starting podcast scraper for {self.feed_url}")
            logger.info(f"preparing build folder at {self.build_dir.resolve()}")

            self.prepare_build_folder()

            if self.s3_url_with_credentials and not self.s3_credentials_ok():
                raise ValueError(
                    "Unable to connect to optimization cache. Check it's URL"
                )

            # fail early if supplied branding files are missing
            self.check_branding_values()

            rss_feed = resolve_url(self.feed_url)

            self.podcast_data = parse_feed(rss_feed)

            logger.info("extracting episodes...")
            self.extract_episodes_list()

            self.episodes_count = len(self.podcast_data.episodes)
            nb_episodes_msg = f".. {self.episodes_count} episodes"
            if self.dateafter_datetime:
                nb_episodes_msg += f" in date range: {self.dateafter_datetime.date()} - {datetime.date.today()}"
            logger.info(f"{nb_episodes_msg}")

            logger.info("update general metadata")
            self.update_metadata()

            if not self.title:
                raise Exception("title is mandatory")
            if not self.description:
                raise Exception("description is mandatory")
            if not self.creator:
                raise Exception("creator is mandatory")

            illustration = "favicon.png"
            illustration_path = self.build_dir / illustration
            if not illustration_path.exists() or not illustration_path.is_file():
                raise OSError(
                    f"Incorrect illustration: {illustration} ({illustration_path})"
                )
            with open(illustration_path, "rb") as fh:
                illustration_data = fh.read()

            logger.info("building ZIM file")
            self.zim_file = Creator(
                filename=self.output_dir / self.fname,
                main_path="index.html",
                ignore_duplicates=True,
            )
            self.zim_file.config_metadata(
                metadata.StandardMetadataList(
                    Name=metadata.NameMetadata(self.fname),
                    Language=metadata.LanguageMetadata(self.language),
                    Title=metadata.TitleMetadata(self.title),
                    Creator=metadata.CreatorMetadata(self.creator),
                    Publisher=metadata.PublisherMetadata(self.publisher),
                    Date=metadata.DateMetadata(
                        datetime.datetime.now(tz=datetime.UTC).date()
                    ),
                    Illustration_48x48_at_1=metadata.DefaultIllustrationMetadata(
                        illustration_data
                    ),
                    Description=metadata.DescriptionMetadata(self.description),
                    LongDescription=(
                        metadata.LongDescriptionMetadata(self.long_description)
                        if self.long_description
                        else None
                    ),
                    Tags=(metadata.TagsMetadata(self.tags) if self.tags else None),
                    Scraper=metadata.ScraperMetadata(SCRAPER),
                )
            )
            self.zim_file.start()

            logger.debug(f"Preparing zim file at {self.zim_file.filename}")

            logger.info("add podcast branding to ZIM")
            self.add_podcast_branding_to_zim()

            logger.debug(f"add zimui files from {self.zimui_dist}")
            self.add_zimui()

            logger.info(f"downloading episodes... (concurrency={self.max_concurrency})")
            if self.s3_storage:
                logger.info(
                    f" using cache: {self.s3_storage.url.netloc} "
                    f"with bucket: {self.s3_storage.bucket_name}"
                )
            succeeded, failed = self.download_episode_files(
                max_concurrency=self.max_concurrency
            )
            if failed:
                logger.error(f"{len(failed)} episode(s) failed to download: {failed}")
                if len(failed) >= len(succeeded):
                    logger.critical(
                        "More than half of the episode(s) failed to download. Exiting..."
                    )
                    raise OSError("Too many episode(s) failed to download")

            logger.info("creating JSON files")
            self.make_json_files(succeeded)

        except KeyboardInterrupt:
            logger.error("KeyboardInterrupt, exiting...")
            return 1
        except Exception as exc:
            logger.error(f"Interrupting process due to error: {exc}")
            logger.exception(exc)
            return 1
        else:
            logger.info("finishing ZIM file...")
            self.zim_file.finish()
        finally:
            self.report_progress()
            logger.info("removing temp folder")
            shutil.rmtree(self.build_dir, ignore_errors=True)

    def report_progress(self):
        if not self.stats_path:
            return
        progress = {
            "done": self.episodes_processed,
            "total": self.episodes_count,
        }
        self.stats_path.write_text(json.dumps(progress, indent=2))

    def validate_dateafter_input(self):
        if not self.dateafter:
            return

        try:
            self.dateafter_datetime = datetime.datetime.strptime(
                self.dateafter, "%Y%m%d"
            ).replace(tzinfo=datetime.timezone.utc)
        except ValueError as exc:
            logger.error("Invalid dateafter input. Valid dateafter format: YYYYMMDD.")
            raise ValueError(f"Invalid dateafter input: {exc}") from exc

        if self.dateafter_datetime > datetime.datetime.now(datetime.UTC):
            error_msg = f"dateafter ({self.dateafter}) cannot be a future date."
            logger.error(error_msg)
            raise ValueError(error_msg)

    def extract_episodes_list(self):
        """apply filters (dateafter, max_episodes) if provided"""

        # Used datetime.min for any episodes missing a date so they drop to the bottom.
        sorted_episodes = sorted(
            self.podcast_data.episodes,
            key=lambda ep: ep.published
            or datetime.datetime.min.replace(tzinfo=datetime.UTC),
            reverse=True,
        )

        filtered = sorted_episodes

        if self.dateafter_datetime:
            filtered = [
                ep
                for ep in filtered
                if ep.published and ep.published >= self.dateafter_datetime
            ]

        if self.max_episodes is not None and self.max_episodes > 0:
            filtered = filtered[: self.max_episodes]

        self.podcast_data.episodes = filtered

    def prepare_build_folder(self):
        """prepare build folder before we start downloading data"""
        self.episodes_dir.mkdir(exist_ok=True)

    def s3_credentials_ok(self):
        logger.info("testing S3 Optimization Cache with credentials")
        self.s3_storage = KiwixStorage(self.s3_url_with_credentials)
        if not self.s3_storage.check_credentials(
            list_buckets=True, bucket=True, write=True, read=True, failsafe=True
        ):
            logger.error("S3 cache connection error testing permissions.")
            logger.error(f"   Server: {self.s3_storage.url.netloc}")
            logger.error(f"   Bucket: {self.s3_storage.bucket_name}")
            logger.error(f"   Key ID: {self.s3_storage.params.get('keyid')}")
            logger.error(f"   Public IP: {get_public_ip()}")
            return False
        return True

    def check_branding_values(self):
        """checks that user-supplied images and colors are valid (so to fail early)

        Images are checked for existence or downloaded then resized
        Colors are checked for validity"""

        # skip if none of related values were supplied
        if not sum(
            [
                bool(x)
                for x in (
                    self.cover_image,
                    self.main_color,
                    self.secondary_color,
                )
            ]
        ):
            return
        logger.info("checking your branding files and values")
        if self.cover_image:
            if isinstance(self.cover_image, str) and self.cover_image.startswith(
                "http"
            ):
                stream_file(self.cover_image, self.cover_path)
            else:
                self.cover_image = Path(self.cover_image)
                if not self.cover_image.exists():
                    raise OSError(
                        f"--cover image could not be found: {self.cover_image}"
                    )
                shutil.copy(self.cover_image, self.cover_path)
            resize_image(self.cover_path, width=100, height=100, method="thumbnail")

        if self.main_color and not is_hex_color(self.main_color):
            raise ValueError(
                f"--main-color is not a valid hex color: {self.main_color}"
            )

        if self.secondary_color and not is_hex_color(self.secondary_color):
            raise ValueError(
                f"--secondary-color is not a valid hex color: {self.secondary_color}"
            )

    def update_metadata(self):
        self.title = self.title or self.podcast_data.title
        auto_description = "\n\n".join(self.podcast_data.description) or "-"
        self.description, self.long_description = compute_descriptions(
            default_description=auto_description,
            user_description=self.description,
            user_long_description=self.long_description,
        )

        if self.creator is None:
            self.creator = self.podcast_data.author or self.podcast_data.title
        self.tags = self.tags or ["podcast"]
        if "_audios:yes" not in self.tags:
            self.tags.append("_audios:yes")

        if not self.cover_path.exists():
            if self.podcast_data.artwork_url:
                # need to get the cover image's ext so it's not hardcoded in add_podcast_branding_to_zim
                self._cover_ext = (
                    Path(urlparse(self.podcast_data.artwork_url).path).suffix or ".jpg"
                )

                stream_file(self.podcast_data.artwork_url, self.cover_path)
            else:
                self._cover_ext = Path(DEFAULT_COVER_PATH).suffix
                shutil.copy(DEFAULT_COVER_PATH, self.cover_path)

        resize_image(self.cover_path, width=100, height=100, method="thumbnail")

        if self.main_color is None or self.secondary_color is None:
            profile_main, profile_secondary = get_colors(self.cover_path)
            self.main_color = self.main_color or profile_main
            self.secondary_color = self.secondary_color or profile_secondary

        # convert cover image to png for favicon
        png_cover_path = self.build_dir.joinpath("cover.png")
        convert_image(self.cover_path, png_cover_path)

        resize_image(
            png_cover_path,
            width=48,
            height=48,
            method="thumbnail",
            dst=self.build_dir.joinpath("favicon.png"),
        )
        png_cover_path.unlink()

    def add_file_to_zim(
        self,
        path: str,
        fpath: Path,
        callback: Callback | list[Callback] | None = None,
    ):
        """add a file to a ZIM file"""
        if not fpath.exists():
            logger.error(f"File {fpath} does not exist")
            return

        logger.debug(f"Adding {path} to ZIM")
        self.zim_file.add_item_for(
            path,
            fpath=fpath,
            callbacks=callback,
        )

    def add_podcast_branding_to_zim(self):
        """add podcast branding to zim file"""
        branding_items = [
            (f"cover{self._cover_ext}", self.cover_path),
            ("favicon.png", self.build_dir / "favicon.png"),
        ]
        for filename, path in branding_items:
            if path.exists():
                self.add_file_to_zim(
                    filename, path, callback=Callback(delete_callback, args=(path,))
                )

    def add_zimui(self):
        """
        Fix for zimui dist folder missing or when user forgets to build the UI
        or if they are using the repo without the UI.
        """
        if not (
            self.zimui_dist.exists()
            and self.zimui_dist.is_dir()
            and any(self.zimui_dist.iterdir())
        ):
            raise ValueError(
                "zimui/dist is empty or missing. Please build the UI first: "
                "cd zimui && yarn install && yarn build"
            )

        logger.info(f"Adding files in {self.zimui_dist}")
        for file in self.zimui_dist.rglob("*"):
            if file.is_dir():
                continue
            path = str(Path(file).relative_to(self.zimui_dist))
            logger.debug(f"Adding {path} to ZIM")
            if path == "index.html":  # change index.html file title and add to ZIM
                index_html_path = self.zimui_dist / path
                html_content = index_html_path.read_text(encoding="utf-8")
                new_html_content = re.sub(
                    r"<title>.*?</title>",
                    f"<title>{self.title}</title>",
                    html_content,
                    flags=re.IGNORECASE,
                )
                self.zim_file.add_item_for(
                    path=path,
                    content=new_html_content,
                    mimetype="text/html",
                    is_front=True,
                )
            else:
                self.zim_file.add_item_for(
                    path=path,
                    fpath=file,
                    is_front=False,
                )

    def download_from_cache(self, key, dest_path, encoder_version=None):
        """Return True if it successfully downloaded from cache"""
        if not self.s3_storage:
            raise Exception(
                "Cannot download from cache if s3_storage is not configured"
            )

        if encoder_version:
            if self.use_any_optimized_version:
                if not self.s3_storage.has_object(key, self.s3_storage.bucket_name):
                    return False
            elif not self.s3_storage.has_object_matching_meta(
                key, tag="encoder_version", value=f"v{encoder_version}"
            ):
                return False
        elif not self.s3_storage.has_object(key, self.s3_storage.bucket_name):
            return False

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.s3_storage.download_file(key, dest_path)
        except Exception as exc:
            logger.error(f"{key} failed to download from cache: {exc}")
            return False
        logger.info(f"downloaded {dest_path} from cache at {key}")
        return True

    def upload_to_cache(self, key, dest_path, encoder_version=None):
        """Return True if successfully uploaded to cache"""
        if not self.s3_storage:
            raise Exception("Cannot upload to cache if s3_storage is not configured")

        try:
            meta = {"encoder_version": f"v{encoder_version}"} if encoder_version else {}
            self.s3_storage.upload_file(dest_path, key, meta=meta)
        except Exception as exc:
            logger.error(f"{key} failed to upload to cache: {exc}")
            return False
        logger.info(f"uploaded {dest_path} to cache at {key}")
        return True

    def download_ep_audio(self, episode: EpisodeData):
        """download the episode's audio from cache or stream it. Return True if successful"""

        episode_location = self.episodes_dir.joinpath(episode.id)
        episode_location.mkdir(parents=True, exist_ok=True)

        audio_url = episode.audio_url
        audio_ext = guess_audio_ext(episode.audio_mimetype, audio_url)

        audio_path = episode_location.joinpath(f"audio{audio_ext}")
        zim_path = f"audios/{episode.id}/audio{audio_ext}"

        s3_key = None

        if self.s3_storage:
            s3_key = zim_path
            logger.debug(
                f"Attempting to download audio file for {episode.title} from cache..."
            )
            if self.download_from_cache(s3_key, audio_path):
                self.add_file_to_zim(
                    zim_path,
                    audio_path,
                    callback=Callback(delete_callback, args=(audio_path,)),
                )
                self.audios_zim_path.update({episode.id: zim_path})
                return True

        try:
            logger.debug(f"Downloading audio file for {episode.title} from {audio_url}")
            stream_file(audio_url, audio_path)

            self.add_file_to_zim(
                zim_path,
                audio_path,
                callback=Callback(delete_callback, args=(audio_path,)),
            )
            self.audios_zim_path.update({episode.id: zim_path})

        except Exception as exc:
            logger.error(f"Audio file for {episode.title} could not be downloaded")
            logger.debug(exc)
            return False
        else:
            if self.s3_storage:
                logger.debug(f"Uploading file for {episode.title} to cache...")
                self.upload_to_cache(s3_key, audio_path)
            return True

    def download_ep_thumbnail(self, episode: EpisodeData):
        """download the episode's thumbnail from cache/stream and return True if successful"""

        episode_location = self.episodes_dir.joinpath(episode.id)
        episode_location.mkdir(parents=True, exist_ok=True)

        thumbnail_path = episode_location.joinpath("thumbnail.webp")
        zim_path = f"audios/{episode.id}/thumbnail.webp"

        preset = WebpHigh()
        s3_key = None

        if self.s3_storage:
            s3_key = zim_path
            logger.debug(f"Attempting to thumbnail for {episode.title} from cache...")
            if self.download_from_cache(s3_key, thumbnail_path, preset.VERSION):
                self.add_file_to_zim(
                    zim_path,
                    thumbnail_path,
                    callback=Callback(delete_callback, args=(thumbnail_path,)),
                )
                return True

        try:
            logger.debug(
                f"Downloading thumbnail for {episode.title} from {episode.thumbnail_url}"
            )
            # to remove type checker warnings
            assert isinstance(episode.thumbnail_url, str)

            parsed_url = urlparse(episode.thumbnail_url)
            ext = Path(parsed_url.path).suffix or "png"
            tmp_thumbnail_path = episode_location.joinpath(f"tmp_thumbnail{ext}")

            stream_file(episode.thumbnail_url, tmp_thumbnail_path)

            convert_image(tmp_thumbnail_path, thumbnail_path)

            self.add_file_to_zim(
                zim_path,
                thumbnail_path,
                callback=Callback(delete_callback, args=(thumbnail_path,)),
            )

            tmp_thumbnail_path.unlink(missing_ok=True)

        except Exception as exc:
            logger.error(f"Thumbnail for {episode.title} could not be downloaded")
            logger.debug(exc)
            return False
        else:
            if self.s3_storage:
                logger.debug(f"Uploading thumbnail for {episode.title} to cache...")
                self.upload_to_cache(s3_key, thumbnail_path, preset.VERSION)
            return True

    def download_episode_files_batch(self, episodes: list[EpisodeData]):
        """
        download episode file and thumbnail for all episodes in batch
        return succeeded and failed episode titles
        """
        succeeded = []
        failed = []
        for episode in episodes:
            # an audio wihtout a thumbnail == success
            logger.info(f"downloading {episode.title!r}")
            if self.download_ep_audio(episode):
                if episode.thumbnail_url and not self.download_ep_thumbnail(episode):
                    logger.warning(
                        f"Thumbnail for {episode.title} failed; continuing without one"
                    )
                succeeded.append(episode.id)
            else:
                failed.append(episode.id)

            with self._progress_lock:
                self.episodes_processed += 1
                done = self.episodes_processed

            logger.info(f"[{done}/{self.episodes_count}] done: {episode.title!r}")
        return succeeded, failed

    def download_episode_files(self, max_concurrency: int):
        # find number of actual parallel workers
        nb_episodes = self.episodes_count
        concurrency = nb_episodes if nb_episodes < max_concurrency else max_concurrency

        # short-circuit concurrency if we have only one thread (can help debug)
        if concurrency <= 1:
            result = self.download_episode_files_batch(self.podcast_data.episodes)
            self.report_progress()
            return result

        # prepare episodes in batches
        def get_slot():
            n = 0
            while True:
                yield n
                n += 1
                if n >= concurrency:
                    n = 0

        batches = [[] for _ in range(0, concurrency)]
        slot = get_slot()
        for episode in self.podcast_data.episodes:
            batches[next(slot)].append(episode)

        overall_succeeded = []
        overall_failed = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            fs = [
                executor.submit(self.download_episode_files_batch, episodes)
                for episodes in batches
            ]

            # as_completed naturally lets each future.result() raise if that
            # future's callable threw and unhandled exception
            for future in concurrent.futures.as_completed(fs):
                succeeded, failed = future.result()
                overall_succeeded += succeeded
                overall_failed += failed

                self.report_progress()

        # remove leftover files for failed downloads
        logger.debug(
            f"removing leftover files of {len(overall_failed)} failed episode(s)"
        )
        for episode_id in overall_failed:
            shutil.rmtree(self.episodes_dir.joinpath(episode_id), ignore_errors=True)

        return overall_succeeded, overall_failed

    def add_custom_item_to_zim_index(
        self, title: str, content: str, fname: str, zimui_redirect: str
    ):
        """add a custom item to the ZIM index"""
        redirect_url = f"../index.html#/{zimui_redirect}"
        html_content = (
            f"<html><head><title>{title}</title>"
            f'<meta http-equiv="refresh" content="0;URL=\'{redirect_url}\'" />'
            f"</head><body></body></html>"
        )

        logger.debug(f"Adding {fname} to ZIM index")
        self.zim_file.add_item_for(
            title=title,
            path=f"index/{fname}",
            content=bytes(html_content, "utf-8"),
            mimetype="text/html",
            index_data=IndexData(title=title, content=content),
        )

    def make_json_files(self, episode_ids: list[str]):
        """Generate JSON files to be consumed by the frontend"""

        def remove_unused_episodes():
            for path in self.episodes_dir.iterdir():
                if path.is_dir() and path.name not in episode_ids:
                    logger.debug(f"Removing unused episode {path.name}")
                    shutil.rmtree(path, ignore_errors=True)

        successful_episodes = [
            ep for ep in self.podcast_data.episodes if ep.id in episode_ids
        ]

        if not successful_episodes:
            raise Exception("No episodes succeeded in downloading")

        episode_previews: list[EpisodePreview] = []

        for ep in successful_episodes:
            thumbnail_path = (
                f"episodes/{ep.id}/thumbnail.webp" if ep.thumbnail_url else None
            )

            audio_ext = guess_audio_ext(ep.audio_mimetype, ep.audio_url)
            audio_path = f"episodes/{ep.id}/audio{audio_ext}"

            published = ep.published.isoformat() if ep.published else ""

            episode_obj = Episode(
                id=ep.id,
                title=ep.title,
                description=ep.description,
                duration=ep.duration,
                published=published,
                audio_path=audio_path,
                thumbnail_path=thumbnail_path,
            )

            # write episodes/{id}.json
            self.zim_file.add_item_for(
                path=f"episodes/{ep.id}.json",
                title=ep.id,
                content=episode_obj.model_dump_json(by_alias=True, indent=2),
                mimetype="application/json",
                is_front=False,
            )

            # add episode to ZIM search index
            # description is a list of str, so join for the index
            self.add_custom_item_to_zim_index(
                episode_obj.title,
                "".join(episode_obj.description),
                ep.id,
                f"episode/{ep.id}",
            )

            episode_previews.append(
                EpisodePreview(
                    id=ep.id,
                    title=ep.title,
                    duration=ep.duration,
                    published=published,
                    thumbnail_path=thumbnail_path,
                )
            )

        podcast_obj = Podcast(
            title=self.podcast_data.title,
            description=self.podcast_data.description,
            author=self.podcast_data.author,
            language=self.podcast_data.language,
            artwork_path=f"cover{self._cover_ext}",
            episode_count=len(episode_previews),
            episodes=episode_previews,
        )

        self.zim_file.add_item_for(
            path="podcast.json",
            title=podcast_obj.title,
            content=podcast_obj.model_dump_json(by_alias=True, indent=2),
            mimetype="application/json",
            is_front=False,
        )

        self.add_custom_item_to_zim_index(
            podcast_obj.title,
            "".join(podcast_obj.description),
            "podcast",
            "podcast",
        )

        self.zim_file.add_item_for(
            path="config.json",
            title="Config",
            content=Config(
                main_color=self.main_color, secondary_color=self.secondary_color
            ).model_dump_json(by_alias=True, indent=2),
            mimetype="application/json",
            is_front=False,
        )
