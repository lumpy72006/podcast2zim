import { defineStore } from 'pinia'

import { useMainStore } from '@/stores/main'
import type { Episode, EpisodePreview } from '@/types/Podcast'

/** The subset of episode data the player actually needs to play something */
export interface PlayingEpisode {
  id: string
  title: string
  thumbnailPath?: string | null
  audioPath: string
  duration: number
}

const toPlayingEpisode = (episode: Episode): PlayingEpisode => ({
  id: episode.id,
  title: episode.title,
  thumbnailPath: episode.thumbnailPath,
  audioPath: episode.audioPath,
  duration: episode.duration
})

export const usePlayerStore = defineStore('player', {
  state: () => ({
    episode: null as PlayingEpisode | null,
    isPlaying: false,
    currentTime: 0,
    mediaDuration: 0,
    speed: 1,
    // bumped only when a genuinely new file needs to be loaded, so the
    // component owning the real <audio> element can tell "new episode"
    // apart from "same episode, just toggling play/pause"
    loadToken: 0,
    // bumped on every seek/skip request; the <audio> owner watches this
    // and applies seekTime, rather than the owner writing currentTime
    // straight back (which would fight with timeupdate every frame)
    seekToken: 0,
    seekTime: 0
  }),
  getters: {
    // prefer the real, measured file length over the feed's often-wrong tag
    duration: (state) =>
      state.mediaDuration > 0 ? state.mediaDuration : (state.episode?.duration ?? 0)
  },
  actions: {
    _start(episode: PlayingEpisode) {
      const isSameEpisode = this.episode?.id === episode.id
      this.episode = episode
      this.isPlaying = true
      if (!isSameEpisode) {
        this.currentTime = 0
        this.mediaDuration = 0
        this.loadToken++
      }
    },
    /** Start playing from a list/header context, where only the preview (no audioPath) is known yet */
    async playPreview(preview: EpisodePreview) {
      if (this.episode?.id === preview.id) {
        this.isPlaying = true
        return
      }
      const main = useMainStore()
      const full = await main.fetchEpisode(preview.id)
      if (full) this._start(toPlayingEpisode(full))
    },
    /** Start playing when the full Episode is already loaded (e.g. on its own page) */
    playEpisode(episode: Episode) {
      this._start(toPlayingEpisode(episode))
    },
    pause() {
      this.isPlaying = false
    },
    toggle() {
      if (!this.episode) return
      this.isPlaying = !this.isPlaying
    },
    seekTo(seconds: number) {
      if (!this.episode) return
      const max = this.duration || Infinity
      this.seekTime = Math.min(Math.max(seconds, 0), max)
      this.currentTime = this.seekTime
      this.seekToken++
    },
    skip(deltaSeconds: number) {
      this.seekTo(this.currentTime + deltaSeconds)
    },
    setSpeed(speed: number) {
      this.speed = speed
    },
    // called by the component that owns the real <audio> element, to report
    // what's actually happening -- never called by any other UI
    reportProgress(seconds: number) {
      this.currentTime = seconds
    },
    reportDuration(seconds: number) {
      if (Number.isFinite(seconds) && seconds > 0) this.mediaDuration = seconds
    },
    reportEnded() {
      this.isPlaying = false
    }
  }
})
