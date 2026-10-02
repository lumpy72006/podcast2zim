<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useMainStore } from '@/stores/main'
import { usePlayerStore } from '@/stores/player'
import { assetUrl, formatClock } from '@/utils/format-utils'
import CoverImage from '@/components/podcast/CoverImage.vue'

const main = useMainStore()
const player = usePlayerStore()
const audio = ref<HTMLAudioElement | null>(null)
const failed = ref(false)

// same "older"/"newer" convention as EpisodeView.vue's prev/next buttons --
// podcast.json lists episodes newest first, so index+1 is older, index-1 newer
const index = computed(
  () => main.podcast?.episodes.findIndex((e) => e.id === player.episode?.id) ?? -1
)
const olderEpisode = computed(() =>
  index.value >= 0 ? main.podcast?.episodes[index.value + 1] : undefined
)
const newerEpisode = computed(() =>
  index.value > 0 ? main.podcast?.episodes[index.value - 1] : undefined
)

const onEnded = () => {
  player.reportEnded()
  if (newerEpisode.value) player.playPreview(newerEpisode.value)
}

// this is the ONLY place in the app that touches a real <audio> element --
// everything else (list rows, header button, the episode page) just reads
// and writes the store, and this watcher makes the real element follow it.
// The <audio> tag itself is rendered unconditionally in the template (not
// gated behind player.episode) specifically so `audio.value` is already
// bound the very first time this watcher ever runs -- gating it previously
// meant the element didn't exist yet on the very first episode played in a
// session, so that first play silently did nothing (no src assigned) while
// the store still thought it was playing; toggling play/pause afterwards
// then called .play() on a still-empty <audio>, which rejects immediately.
watch(
  () => [player.loadToken, player.isPlaying] as const,
  ([loadToken, isPlaying], previous) => {
    const el = audio.value
    if (!el || !player.episode) return

    const isNewFile = !previous || loadToken !== previous[0]
    // A native <audio> element does NOT self-heal after a failed load --
    // once el.error is set, calling .play() again keeps failing forever,
    // even on a perfectly valid file, until src is explicitly reassigned.
    // So retry (same episode, after a failure) needs a reload too, not
    // only a genuinely new episode -- otherwise one transient failure
    // poisons that episode until you happen to load a different one.
    const needsReload = isNewFile || el.error != null || !el.src
    if (needsReload) {
      failed.value = false
      const resumeAt = isNewFile ? 0 : player.currentTime
      el.src = assetUrl(player.episode.audioPath) ?? ''
      el.playbackRate = player.speed
      if (resumeAt > 0) {
        const restorePosition = () => {
          el.currentTime = resumeAt
          el.removeEventListener('loadedmetadata', restorePosition)
        }
        el.addEventListener('loadedmetadata', restorePosition)
      }
    }

    if (isPlaying) {
      el.play().catch(() => {
        failed.value = true
        player.pause()
      })
    } else {
      el.pause()
    }
  }
)

// applies a seek/skip request coming from any UI (list row, header, episode page)
watch(
  () => player.seekToken,
  () => {
    if (audio.value) audio.value.currentTime = player.seekTime
  }
)

watch(
  () => player.speed,
  (speed) => {
    if (audio.value) audio.value.playbackRate = speed
  }
)

const onTimeUpdate = () => {
  if (audio.value) player.reportProgress(audio.value.currentTime)
}
const onLoadedMetadata = () => {
  if (audio.value) player.reportDuration(audio.value.duration)
}
</script>

<template>
  <!-- unconditional on purpose -- see the comment above the watcher -->
  <audio
    ref="audio"
    preload="metadata"
    @timeupdate="onTimeUpdate"
    @loadedmetadata="onLoadedMetadata"
    @durationchange="onLoadedMetadata"
    @ended="onEnded"
    @error="failed = true"
  ></audio>

  <div v-if="player.episode" class="persistent-player border-thin rounded-lg">
    <div class="seek-wrap">
      <v-slider
        :model-value="player.currentTime"
        :max="player.duration || 1"
        :disabled="!player.duration"
        color="primary"
        hide-details
        density="compact"
        class="seek-slider"
        aria-label="Seek"
        @update:model-value="player.seekTo($event)"
      />
    </div>

    <div class="d-flex align-center ga-2 px-3 pb-2">
      <router-link
        :to="{ name: 'episode', params: { id: player.episode.id } }"
        class="d-flex align-center ga-3 min-width-0 flex-grow-1 player-link"
      >
        <div class="thumb flex-shrink-0">
          <cover-image :path="player.episode.thumbnailPath" :alt="player.episode.title" />
        </div>
        <div class="min-width-0">
          <p class="text-body-2 font-weight-medium text-truncate">{{ player.episode.title }}</p>
          <p v-if="failed" class="text-caption text-error">Playback failed. Tap play to retry.</p>
          <p v-else class="text-caption text-medium-emphasis">
            {{ formatClock(player.currentTime) }} /
            {{ player.duration ? formatClock(player.duration) : '--:--' }}
          </p>
        </div>
      </router-link>

      <v-btn
        icon="mdi-rewind-15"
        variant="text"
        density="comfortable"
        aria-label="Back 15 seconds"
        @click="player.skip(-15)"
      />
      <v-btn
        icon="mdi-skip-previous"
        variant="text"
        density="comfortable"
        aria-label="Older episode"
        :disabled="!olderEpisode"
        @click="olderEpisode && player.playPreview(olderEpisode)"
      />
      <v-btn
        :icon="player.isPlaying ? 'mdi-pause' : 'mdi-play'"
        color="primary"
        density="comfortable"
        :aria-label="player.isPlaying ? 'Pause' : 'Play'"
        @click="player.toggle()"
      />
      <v-btn
        icon="mdi-skip-next"
        variant="text"
        density="comfortable"
        aria-label="Newer episode"
        :disabled="!newerEpisode"
        @click="newerEpisode && player.playPreview(newerEpisode)"
      />
      <v-btn
        icon="mdi-fast-forward-15"
        variant="text"
        density="comfortable"
        aria-label="Forward 15 seconds"
        @click="player.skip(15)"
      />
    </div>
  </div>
</template>

<style scoped>
.persistent-player {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 16px;
  width: min(720px, calc(100% - 24px));
  z-index: 1000;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.3);
}

/* keeps the slider's thumb from sitting flush against the pill's rounded
   edges -- the slider itself has a negative inline margin built in to
   enlarge its touch target, so padding alone on this wrapper isn't enough */
.seek-wrap {
  padding: 10px 20px 0;
}

.seek-slider :deep(.v-slider__container) {
  margin-inline: 4px;
}

.thumb {
  width: 40px;
}

.min-width-0 {
  min-width: 0;
}

.player-link {
  text-decoration: none;
  color: inherit;
}
</style>
