import argparse
import logging
import os
import sys
from pathlib import Path

from podcast2zim.constants import NAME, SCRAPER, logger
from podcast2zim.scraper import Podcast2Zim


def main():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Scraper to create a ZIM file from a podcast using RSS/Atom feeds or Apple iTunes URL.",
    )

    parser.add_argument(
        "--feed-url",
        help="RSS/Atom feed or Apple iTunes URL.",
        required=True,
    )
    parser.add_argument(
        "--name",
        help="ZIM name. Used as identifier and filename (date will be appended).",
        required=True,
    )
    parser.add_argument(
        "--output",
        help="Output folder for ZIM file.",
        default="output/",
        dest="output_dir",
    )
    parser.add_argument(
        "--zim-file",
        help="ZIM file name (based on --name if not provided). "
        "If used, {period} is replaced with date as of YYYY-MM.",
        dest="fname",
    )
    parser.add_argument(
        "--stats-filename",
        help="Path to store the progress JSON file to.",
    )
    parser.add_argument(
        "--tmp-dir",
        help="Path to create temp folder in. "
        "Used to temporarily store downloaded files before adding to ZIM.",
    )
    parser.add_argument(
        "--zimui-dist",
        type=str,
        help="Directory containing Vite build output from the ZIM UI Vue.JS application.",
        default=os.getenv(
            "PODCAST_ZIMUI_DIST",
            str(Path(__file__).parent / "zimui"),
        ),
    )
    parser.add_argument(
        "--optimization-cache",
        help="URL with credentials to S3 for using as optimization cache.",
        dest="s3_url_with_credentials",
    )
    parser.add_argument(
        "--use-any-optimized-version",
        help="Use the cached files if present.",
        action="store_true",  # defaults to False
    )
    parser.add_argument("--debug", help="Enable verbose output.", action="store_true")
    parser.add_argument(
        "--concurrency",
        help="Number of concurrent threads to use",
        type=int,
        dest="max_concurrency",
        default=1,
    )
    parser.add_argument(
        "--title",
        help="Custom title for your project and ZIM. Defaults podcast's name.",
    )
    parser.add_argument(
        "--creator",
        help="Name of podcast's creator. Defaults to the podcast's author.",
    )
    parser.add_argument(
        "--publisher",
        help="Custom publisher name (ZIM metadata)",
        default="openZIM",
    )
    parser.add_argument(
        "--description",
        help="Custom description for your project and ZIM. "
        "Defaults to podcast level summary.",
    )
    parser.add_argument(
        "--long-description", help="Custom long description for your ZIM."
    )
    parser.add_argument(
        "--language",
        help="ISO-639-3 (3 chars) language code of content",
        default="eng",
    )
    parser.add_argument(
        "--tags",
        help="Comma separated tags for the ZIM file. _audios:yes added automatically",
        default="podcast",
    )
    parser.add_argument(
        "--cover-image",
        help="Custom cover image (path or URL). Squared. Will be resized to 100x100.",
    )
    parser.add_argument(
        "--main-color",
        help="Custom color. Hex/HTML syntax (#DEDEDE). "
        "Default to main color of cover image.",
    )
    parser.add_argument(
        "--secondary-color",
        help="Custom secondary color. Hex/HTML syntax (#DEDEDE). "
        "Default to secondary color of cover image.",
    )
    parser.add_argument(
        "--max-episodes",
        help="Number of episodes to download from the podcast.",
        type=int,
    )
    parser.add_argument(
        "--dateafter",
        help="Custom filter to download episodes uploaded on or after specified date. "
        "Format: YYYYMMDD",
    )

    args = parser.parse_args()
    args_dict = vars(args)
    # debug is never used in the scraper, best popped here
    is_debug = args_dict.pop("debug", False)
    logger.setLevel(logging.DEBUG if is_debug else logging.INFO)

    try:
        if args.max_concurrency < 1:
            raise ValueError(f"Invalid concurrency value: {args.max_concurrency}")
        scraper = Podcast2Zim(**args_dict)

        # print(args)
        # print()
        # print(args_dict)
        # print()
        # print(scraper)
        # print(str(Path(__file__).parent / "zimui"))
        return scraper.run()
    except Exception as exc:
        logger.error(f"FAILED. An error occured: {exc}")
        if is_debug:
            logger.exception(exc)


if __name__ == "__main__":
    sys.exit(main())
