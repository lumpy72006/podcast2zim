from humps import camelize
from pydantic import BaseModel


class CamelModel(BaseModel):
    """Model to transform Pyhton snake_case into JSON camelCase"""

    class Config:
        alias_generator = camelize
        populate_by_name = True


class Episode(CamelModel):
    """Class to serialize data about a podcast episode"""

    id: str
    title: str
    description: list[str]
    duration: int
    published: str
    audio_path: str
    thumbnail_path: str | None = None


class EpisodePreview(CamelModel):
    """Class to serialize data about a podcast episode for preview"""

    id: str
    title: str
    duration: int
    published: str
    thumbnail_path: str | None = None


class Podcast(CamelModel):
    """Class to serialize data about a podcast"""

    title: str
    description: list[str]
    author: str
    language: str
    artwork_path: str | None = None
    episode_count: int
    episodes: list[EpisodePreview]


class Config(CamelModel):
    """Class to serialize configuration data for the ZIM UI."""

    main_color: str | None
    secondary_color: str | None
