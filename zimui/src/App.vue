<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useMainStore } from '@/stores/main'
import { usePlayerStore } from '@/stores/player'

import ErrorDisplay from '@/components/common/ErrorDisplay.vue'
import PersistentPlayer from '@/components/player/PersistentPlayer.vue'

const main = useMainStore()
const player = usePlayerStore()
</script>

<template>
  <v-app>
    <v-main :class="{ 'has-persistent-player': player.episode }">
      <div v-if="main.errorMessage">
        <error-display />
      </div>
      <div v-else>
        <router-view />
      </div>
    </v-main>
    <persistent-player />
  </v-app>
</template>

<style scoped>
/* reserve room so the fixed bottom player never covers page content */
.has-persistent-player {
  padding-bottom: 104px;
}
</style>
