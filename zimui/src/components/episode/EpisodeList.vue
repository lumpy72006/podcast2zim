<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'

import { useMainStore } from '@/stores/main'
import type { EpisodePreview } from '@/types/Podcast'
import EpisodeCard from '@/components/episode/EpisodeCard.vue'

const { mdAndDown } = useDisplay()
const main = useMainStore()

const props = defineProps<{
  episodes: EpisodePreview[]
}>()

const PAGE_SIZE = 24

const query = ref('')
const visibleCount = ref(PAGE_SIZE)

// podcast.json is newest first; filter by title and apply the chosen order
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = q ? props.episodes.filter((e) => e.title.toLowerCase().includes(q)) : props.episodes
  return main.episodesNewestFirst ? list : [...list].reverse()
})

const items = computed(() => filtered.value.slice(0, visibleCount.value))

// start again from the first page whenever the list changes
watch([query, () => main.episodesNewestFirst], () => {
  visibleCount.value = PAGE_SIZE
})

const load = ({ done }: { done: (status: 'ok' | 'empty') => void }) => {
  visibleCount.value += PAGE_SIZE
  done(visibleCount.value >= filtered.value.length ? 'empty' : 'ok')
}
</script>

<template>
  <v-container class="px-1" :fluid="mdAndDown">
    <v-row dense class="px-2 pb-2" align="center">
      <v-col cols="12" sm>
        <v-text-field
          v-model="query"
          density="compact"
          variant="outlined"
          hide-details
          clearable
          placeholder="Search episodes"
          prepend-inner-icon="mdi-magnify"
        />
      </v-col>
      <v-col cols="12" sm="auto" class="d-flex justify-end">
        <v-btn
          variant="text"
          :prepend-icon="
            main.episodesNewestFirst ? 'mdi-sort-calendar-descending' : 'mdi-sort-calendar-ascending'
          "
          @click="main.toggleEpisodesSortOrder()"
        >
          {{ main.episodesNewestFirst ? 'Newest first' : 'Oldest first' }}
        </v-btn>
      </v-col>
    </v-row>

    <p v-if="filtered.length === 0" class="text-center text-medium-emphasis py-8">
      No episodes found.
    </p>
    <v-infinite-scroll
      v-else
      :key="`${query}-${main.episodesNewestFirst}`"
      class="h-full overflow-hidden"
      :items="items"
      empty-text=""
      @load="load"
    >
      <v-row dense>
        <v-col v-for="episode in items" :key="episode.id" cols="12" md="6">
          <episode-card :episode="episode" />
        </v-col>
      </v-row>
    </v-infinite-scroll>
  </v-container>
</template>
