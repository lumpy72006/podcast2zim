<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { assetUrl } from '@/utils/format-utils'

const props = withDefaults(
  defineProps<{
    /** ZIM path such as "cover.jpg" or "episodes/<id>/thumbnail.webp" */
    path?: string | null
    alt?: string
    rounded?: string
  }>(),
  { path: null, alt: '', rounded: 'lg' }
)

// If the image is missing (e.g. a thumbnail that failed to download) show an icon instead
const failed = ref(false)
watch(
  () => props.path,
  () => {
    failed.value = false
  }
)
const src = computed(() => (failed.value ? undefined : assetUrl(props.path)))
</script>

<template>
  <v-img
    v-if="src"
    :src="src"
    :alt="alt"
    aspect-ratio="1"
    cover
    :class="`rounded-${rounded} border-thin`"
    @error="failed = true"
  >
    <template #placeholder>
      <div class="d-flex align-center justify-center fill-height bg-surface">
        <v-progress-circular indeterminate size="24" width="2" />
      </div>
    </template>
  </v-img>
  <div
    v-else
    :class="`rounded-${rounded} border-thin d-flex align-center justify-center cover-fallback`"
    role="img"
    :aria-label="alt"
  >
    <v-icon icon="mdi-podcast" size="40%" color="on-primary" />
  </div>
</template>

<style scoped>
.cover-fallback {
  aspect-ratio: 1;
  width: 100%;
  background: linear-gradient(
    135deg,
    rgb(var(--v-theme-primary-darken-1)) 0%,
    rgb(var(--v-theme-primary)) 100%
  );
}
</style>
