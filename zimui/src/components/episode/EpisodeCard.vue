<script setup lang="ts">
import { computed } from 'vue'

import type { EpisodePreview } from '@/types/Podcast'
import { formatDate, formatDuration } from '@/utils/format-utils'
import { usePlayerStore } from '@/stores/player'
import CoverImage from '@/components/podcast/CoverImage.vue'

const props = defineProps<{
  episode: EpisodePreview
}>()

const player = usePlayerStore()

const meta = computed(() =>
  [formatDate(props.episode.published), formatDuration(props.episode.duration)]
    .filter(Boolean)
    .join(' · ')
)

const isCurrent = computed(() => player.episode?.id === props.episode.id)
const isPlaying = computed(() => isCurrent.value && player.isPlaying)

// this is the row's own control: it must not trigger the row's link navigation
const onPlayClick = () => {
  if (isCurrent.value) {
    player.toggle()
  } else {
    player.playPreview(props.episode)
  }
}
</script>

<template>
  <router-link :to="{ name: 'episode', params: { id: props.episode.id } }" class="episode-link">
    <v-card flat class="episode-card bg-transparent rounded-lg pa-2">
      <div class="d-flex align-center ga-4">
        <div class="thumb flex-shrink-0">
          <cover-image :path="props.episode.thumbnailPath" :alt="props.episode.title" />
        </div>
        <div class="flex-grow-1 min-width-0">
          <p class="episode-title text-body-1 font-weight-medium text-on-surface">
            {{ props.episode.title }}
          </p>
          <p v-if="props.episode.summary" class="episode-summary text-body-2 text-medium-emphasis mt-1">
            {{ props.episode.summary }}
          </p>
          <p v-if="meta" class="text-caption text-medium-emphasis mt-1">{{ meta }}</p>
        </div>
        <v-btn
          :icon="isPlaying ? 'mdi-pause-circle-outline' : 'mdi-play-circle-outline'"
          variant="text"
          size="32"
          color="primary"
          class="flex-shrink-0"
          :aria-label="isPlaying ? 'Pause episode' : 'Play episode'"
          @click.stop.prevent="onPlayClick"
        />
      </div>
    </v-card>
  </router-link>
</template>

<style scoped>
.episode-link {
  display: block;
}

.episode-card:hover {
  background: rgba(var(--v-theme-on-surface), 0.06) !important;
}

.thumb {
  width: 72px;
}

.min-width-0 {
  min-width: 0;
}

/* keep long titles to two lines */
.episode-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

/* truncate long episode summaries to two lines, like Spotify's episode rows */
.episode-summary {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
</style>
