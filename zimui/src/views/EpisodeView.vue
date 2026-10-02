<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

import { useMainStore } from '@/stores/main'
import { usePlayerStore } from '@/stores/player'
import type { Episode } from '@/types/Podcast'
import { formatDate, formatDuration } from '@/utils/format-utils'
import { formatDescription } from '@/utils/description-utils'
import AudioPlayer from '@/components/episode/AudioPlayer.vue'
import CoverImage from '@/components/podcast/CoverImage.vue'

const route = useRoute()
const main = useMainStore()
const player = usePlayerStore()
const { mdAndDown } = useDisplay()

const episode = ref<Episode>()
const isLoading = ref(true)

// vue-router gives the decoded id, exactly as stored in podcast.json
const episodeId = computed(() => String(route.params.id))

const load = async () => {
  isLoading.value = true
  episode.value = undefined
  try {
    // podcast.json is needed for prev/next and for deep links opened from ZIM search
    await main.fetchPodcast()
    const data = await main.fetchEpisode(episodeId.value)
    if (data) {
      episode.value = data
      document.title = `${data.title} - ${main.podcast?.title ?? ''}`.replace(/ - $/, '')
    }
  } catch (error) {
    console.error('Error fetching episode:', error)
    main.setErrorMessage('An unexpected error occurred when fetching the episode.')
  } finally {
    isLoading.value = false
  }
}

watch(episodeId, load, { immediate: true })

// episodes are listed newest first
const index = computed(() => main.podcast?.episodes.findIndex((e) => e.id === episodeId.value) ?? -1)
const newer = computed(() => (index.value > 0 ? main.podcast?.episodes[index.value - 1] : undefined))
const older = computed(() =>
  index.value >= 0 ? main.podcast?.episodes[index.value + 1] : undefined
)

// fall back to the podcast cover when the episode has no thumbnail of its own
const artwork = computed(() => episode.value?.thumbnailPath || main.podcast?.artworkPath)
const description = computed(() => formatDescription(episode.value?.summary ?? ''))

// the feed's <itunes:duration> is frequently wrong (dynamic ad insertion
// changes the real file length); once this episode is the one actually
// loaded in the shared player, show its real measured duration instead
const isCurrent = computed(() => player.episode?.id === episode.value?.id)
const displayDuration = computed(() =>
  isCurrent.value && player.duration ? player.duration : (episode.value?.duration ?? 0)
)
const meta = computed(() =>
  [formatDate(episode.value?.published ?? ''), formatDuration(displayDuration.value)]
    .filter(Boolean)
    .join(' · ')
)
</script>

<template>
  <v-container class="episode-view" :fluid="mdAndDown">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="{ name: 'home' }" class="mb-2">
      {{ main.podcast?.title || 'All episodes' }}
    </v-btn>

    <div v-if="isLoading" class="mt-8 d-flex justify-center">
      <v-progress-circular indeterminate />
    </div>

    <v-row v-else-if="episode">
      <v-col cols="12" md="4" lg="3">
        <div class="cover-wrap mx-auto">
          <cover-image :path="artwork" :alt="episode.title" />
        </div>
      </v-col>
      <v-col cols="12" md="8" lg="9">
        <h1 class="text-h5 text-md-h4 font-weight-bold text-wrap">{{ episode.title }}</h1>
        <p v-if="meta" class="text-body-2 text-medium-emphasis mt-1 mb-4">{{ meta }}</p>

        <audio-player :episode="episode" />

        <div class="d-flex justify-space-between mt-3">
          <v-btn
            v-if="older"
            variant="text"
            prepend-icon="mdi-skip-previous"
            :to="{ name: 'episode', params: { id: older.id } }"
          >
            Older
          </v-btn>
          <v-spacer />
          <v-btn
            v-if="newer"
            variant="text"
            append-icon="mdi-skip-next"
            :to="{ name: 'episode', params: { id: newer.id } }"
          >
            Newer
          </v-btn>
        </div>

        <h2 class="text-h6 mt-6 mb-2">About this episode</h2>
        <p class="description text-body-1">
          <template v-for="([text, tag], i) in description" :key="i">
            <a v-if="tag === 'a'" :href="text" target="_blank" rel="noopener noreferrer">{{
              text
            }}</a>
            <br v-else-if="tag === 'br'" />
            <span v-else>{{ text }}</span>
          </template>
        </p>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.cover-wrap {
  max-width: 260px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  border-radius: 12px;
}

.description {
  white-space: pre-wrap;
  word-break: break-word;
}

.description a {
  color: rgb(var(--v-theme-primary));
}
</style>
