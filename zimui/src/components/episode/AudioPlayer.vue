<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { formatClock } from '@/utils/format-utils'

const props = defineProps<{
  src: string
  /** duration from the feed, used until the audio file reports its own */
  fallbackDuration?: number
}>()

// lets the parent (e.g. the episode header) show the real duration too,
// once it's known — feed-declared durations are frequently wrong
const emit = defineEmits<{
  duration: [seconds: number]
}>()

const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2]

const audio = ref<HTMLAudioElement | null>(null)
const playing = ref(false)
const currentTime = ref(0)
const mediaDuration = ref(0)
const speed = ref(1)
const failed = ref(false)
const buffering = ref(false)
// while the user drags the slider we must not overwrite it with timeupdate events
const seeking = ref(false)

const duration = computed(() =>
  Number.isFinite(mediaDuration.value) && mediaDuration.value > 0
    ? mediaDuration.value
    : props.fallbackDuration || 0
)

const togglePlay = () => {
  const el = audio.value
  if (!el) return
  if (el.paused) {
    // play() returns a promise that rejects if playback is blocked or fails
    el.play().catch((error) => {
      console.error('Unable to play audio:', error)
    })
  } else {
    el.pause()
  }
}

const skip = (seconds: number) => {
  const el = audio.value
  if (!el) return
  const max = duration.value || Infinity
  el.currentTime = Math.min(Math.max(el.currentTime + seconds, 0), max)
  currentTime.value = el.currentTime
}

const onSeekInput = (value: number) => {
  seeking.value = true
  currentTime.value = value
}

const onSeekCommit = (value: number) => {
  if (audio.value) audio.value.currentTime = value
  currentTime.value = value
  seeking.value = false
}

const setSpeed = (value: number) => {
  speed.value = value
  if (audio.value) audio.value.playbackRate = value
}

const onTimeUpdate = () => {
  if (!seeking.value && audio.value) currentTime.value = audio.value.currentTime
}

const onLoadedMetadata = () => {
  if (!audio.value) return
  mediaDuration.value = audio.value.duration
  audio.value.playbackRate = speed.value
  if (Number.isFinite(mediaDuration.value) && mediaDuration.value > 0) {
    emit('duration', mediaDuration.value)
  }
}

// a new episode was opened: reset the state (the <audio> element is reused)
watch(
  () => props.src,
  () => {
    playing.value = false
    currentTime.value = 0
    mediaDuration.value = 0
    failed.value = false
    buffering.value = false
  }
)

onBeforeUnmount(() => {
  audio.value?.pause()
})
</script>

<template>
  <v-card flat class="player border-thin rounded-lg pa-4">
    <audio
      ref="audio"
      :key="props.src"
      :src="props.src"
      preload="metadata"
      @play="playing = true"
      @pause="playing = false"
      @ended="playing = false"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @durationchange="onLoadedMetadata"
      @waiting="buffering = true"
      @playing="buffering = false"
      @canplay="buffering = false"
      @error="failed = true"
    ></audio>

    <v-alert v-if="failed" type="error" variant="tonal" density="compact" class="mb-3">
      The audio file could not be loaded.
    </v-alert>

    <v-slider
      :model-value="currentTime"
      :max="duration || 1"
      :disabled="failed || !duration"
      color="primary"
      hide-details
      density="compact"
      aria-label="Seek"
      @update:model-value="onSeekInput"
      @end="onSeekCommit"
    />
    <div class="d-flex justify-space-between text-caption text-medium-emphasis">
      <span>{{ formatClock(currentTime) }}</span>
      <span>{{ duration ? formatClock(duration) : '--:--' }}</span>
    </div>

    <div class="d-flex align-center justify-center ga-2 mt-2">
      <v-menu>
        <template #activator="{ props: menuProps }">
          <v-btn v-bind="menuProps" variant="text" size="small" class="speed-btn">
            {{ speed }}x
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item
            v-for="s in SPEEDS"
            :key="s"
            :active="s === speed"
            :title="`${s}x`"
            @click="setSpeed(s)"
          />
        </v-list>
      </v-menu>

      <v-btn
        icon="mdi-rewind-15"
        variant="text"
        aria-label="Back 15 seconds"
        :disabled="failed"
        @click="skip(-15)"
      />
      <v-btn
        :icon="playing ? 'mdi-pause' : 'mdi-play'"
        color="primary"
        size="x-large"
        :loading="buffering && playing"
        :aria-label="playing ? 'Pause' : 'Play'"
        :disabled="failed"
        @click="togglePlay"
      />
      <v-btn
        icon="mdi-fast-forward-15"
        variant="text"
        aria-label="Forward 15 seconds"
        :disabled="failed"
        @click="skip(15)"
      />
      <!-- keeps the play button centred against the speed button -->
      <div class="speed-spacer"></div>
    </div>
  </v-card>
</template>

<style scoped>
.speed-btn,
.speed-spacer {
  min-width: 56px;
}
.speed-spacer {
  width: 56px;
}
</style>
