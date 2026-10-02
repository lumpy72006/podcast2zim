<script setup lang="ts">
// This is a *control* only -- it has no <audio> element of its own.
// Playback is shared app-wide state owned by the player store, and the
// real <audio> element (plus all the actual controls: seek, skip, speed,
// older/newer) lives in PersistentPlayer.vue, the bar fixed to the bottom
// of the screen. This button just starts/resumes this episode there, or
// reflects its state when it's already the one playing.
import { computed } from 'vue'

import { usePlayerStore } from '@/stores/player'
import type { Episode } from '@/types/Podcast'

const props = defineProps<{
  episode: Episode
}>()

const player = usePlayerStore()

const isPlaying = computed(() => player.episode?.id === props.episode.id && player.isPlaying)

const togglePlay = () => {
  if (player.episode?.id === props.episode.id) {
    player.toggle()
  } else {
    player.playEpisode(props.episode)
  }
}
</script>

<template>
  <div class="d-flex justify-center">
    <v-btn
      :icon="isPlaying ? 'mdi-pause' : 'mdi-play'"
      color="primary"
      size="x-large"
      :aria-label="isPlaying ? 'Pause' : 'Play'"
      @click="togglePlay"
    />
  </div>
</template>
