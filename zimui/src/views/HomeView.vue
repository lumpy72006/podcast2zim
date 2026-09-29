<script setup lang="ts">
import { onMounted, watch } from 'vue'

import { useMainStore } from '@/stores/main'
import PodcastHeader from '@/components/podcast/PodcastHeader.vue'
import EpisodeList from '@/components/episode/EpisodeList.vue'

const main = useMainStore()

onMounted(async () => {
  try {
    await main.fetchPodcast()
  } catch {
    main.setErrorMessage('An unexpected error occured.')
  }
})

// Update the document title with the podcast title
watch(
  () => main.podcast,
  () => {
    if (main.podcast) document.title = main.podcast.title
  },
  { immediate: true }
)
</script>

<template>
  <div v-if="main.isLoading && !main.podcast" class="mt-8 d-flex justify-center">
    <v-progress-circular indeterminate />
  </div>
  <template v-else-if="main.podcast">
    <podcast-header />
    <episode-list :episodes="main.podcast.episodes" />
  </template>
</template>
