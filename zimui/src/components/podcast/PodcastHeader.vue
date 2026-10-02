<script setup lang="ts">
import { computed } from 'vue'
import { useDisplay } from 'vuetify'

import { useMainStore } from '@/stores/main'
import { usePlayerStore } from '@/stores/player'
import CoverImage from '@/components/podcast/CoverImage.vue'
import AboutDialogButton from '@/components/podcast/AboutDialogButton.vue'

const { mdAndDown, smAndDown } = useDisplay()
const main = useMainStore()
const player = usePlayerStore()

// podcast.json lists episodes newest first
const latestEpisode = computed(() => main.podcast?.episodes[0])
const isPlayingLatest = computed(
  () => !!latestEpisode.value && player.episode?.id === latestEpisode.value.id && player.isPlaying
)

const togglePlayLatest = () => {
  if (isPlayingLatest.value) {
    player.toggle()
  } else if (latestEpisode.value) {
    player.playPreview(latestEpisode.value)
  }
}
</script>

<template>
  <v-container class="pt-0 pt-md-4 px-0 px-md-4" :fluid="mdAndDown">
    <v-card flat class="header-card border-thin border-t-0 rounded-lg">
      <div class="header-bg rounded-lg rounded-t-0 pa-6 pa-md-8">
        <v-row align="center">
          <v-col cols="12" md="auto" class="d-flex justify-center">
            <div class="cover-box">
              <cover-image :path="main.podcast?.artworkPath" :alt="main.podcast?.title" />
            </div>
          </v-col>
          <v-col cols="12" md class="text-center text-md-left header-text">
            <p class="text-overline">Podcast</p>
            <h1 :class="smAndDown ? 'text-h5' : 'text-h4'" class="font-weight-bold text-wrap">
              {{ main.podcast?.title }}
            </h1>
            <p v-if="main.podcast?.author" class="text-subtitle-1 mt-1">
              {{ main.podcast.author }}
            </p>
            <p class="text-body-2 mt-1">
              <v-icon icon="mdi-microphone-outline" size="small" class="mr-1" />
              {{ main.podcast?.episodeCount }}
              {{ main.podcast?.episodeCount === 1 ? 'episode' : 'episodes' }}
            </p>
            <div class="d-flex flex-wrap ga-3 mt-4 justify-center justify-md-start">
              <v-btn
                v-if="latestEpisode"
                variant="flat"
                class="play-btn"
                :prepend-icon="isPlayingLatest ? 'mdi-pause' : 'mdi-play'"
                @click="togglePlayLatest"
              >
                {{ isPlayingLatest ? 'Playing latest' : 'Play latest' }}
              </v-btn>
              <about-dialog-button
                v-if="main.podcast"
                :title="main.podcast.title"
                :author="main.podcast.author"
                :description="main.podcast.summary"
                :language="main.podcast.language"
                :episode-count="main.podcast.episodeCount"
              />
            </div>
          </v-col>
        </v-row>
      </div>
    </v-card>
  </v-container>
</template>

<style scoped>
/* Make border zero on .header-card for mobile screens less that 960 px*/
@media (max-width: 960px) {
  .header-card {
    border-left: 0 !important;
    border-right: 0 !important;
    border-top-left-radius: 0 !important;
    border-top-right-radius: 0 !important;
  }
}

.header-bg {
  color: rgb(var(--v-theme-on-primary));
  background: linear-gradient(
    120deg,
    rgba(var(--v-theme-primary-darken-1)) 0%,
    rgba(var(--v-theme-primary)) 50%,
    rgba(var(--v-theme-primary-lighten-1)) 100%
  );
}

.cover-box {
  width: 180px;
  max-width: 100%;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  border-radius: 12px;
}

.play-btn {
  background: rgb(var(--v-theme-on-primary)) !important;
  color: rgb(var(--v-theme-primary)) !important;
}

.header-text {
  min-width: 0;
}
</style>
