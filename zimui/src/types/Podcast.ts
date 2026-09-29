// Mirrors the JSON written by podcast2zim (see schemas.py, camelCase aliases)

export interface Config {
  mainColor?: string | null
  secondaryColor?: string | null
}

export interface EpisodePreview {
  id: string
  title: string
  summary: string
  /** length in seconds (0 when the feed did not provide it) */
  duration: number
  /** ISO 8601 date, or '' when unknown */
  published: string
  thumbnailPath?: string | null
}

export interface Episode extends EpisodePreview {
  audioPath: string
}

export interface Podcast {
  title: string
  summary: string
  author: string
  language: string
  artworkPath?: string | null
  episodeCount: number
  episodes: EpisodePreview[]
}
