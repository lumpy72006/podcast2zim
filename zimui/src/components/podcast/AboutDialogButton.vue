<script setup lang="ts">
import { ref } from 'vue'

const dialog = ref<boolean>(false)
const props = defineProps<{
  title: string
  author: string
  description: string
  language: string
  episodeCount: number
}>()

const notAvailable = 'Not available'
</script>

<template>
  <v-btn class="border-thin" variant="outlined" @click="dialog = true">
    <v-icon icon="mdi-information-outline" start></v-icon>
    About podcast
  </v-btn>
  <v-dialog v-model="dialog" width="500" scrollable>
    <v-card prepend-icon="mdi-information-outline" title="About" class="rounded-lg">
      <v-card-text>
        <v-row>
          <v-col cols="12">
            <p class="text-h6">Podcast</p>
            <p>{{ props.title || notAvailable }}</p>
          </v-col>
          <v-col cols="12">
            <p class="text-h6">Author</p>
            <p>{{ props.author || notAvailable }}</p>
          </v-col>
          <v-col cols="12">
            <p class="text-h6">Description</p>
            <p class="text-pre-wrap">{{ props.description || notAvailable }}</p>
          </v-col>
          <v-col cols="6">
            <p class="text-h6">Language</p>
            <p>{{ props.language || notAvailable }}</p>
          </v-col>
          <v-col cols="6">
            <p class="text-h6">Episodes</p>
            <p>{{ props.episodeCount }}</p>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn class="ms-auto" @click="dialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
