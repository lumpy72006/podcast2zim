// A minimal custom Vuetify icon set: only the handful of icons this app
// actually uses, each mapped by the exact "mdi-xxx" name already used
// throughout the components (so every existing icon="mdi-xxx" prop keeps
// working unchanged -- nothing elsewhere needed to change).
//
// This replaces @mdi/font, which bundles every Material Design icon --
// thousands of them -- into ~3.6MB of font files shipped inside the ZIM
// regardless of the ~15 icons actually used. @mdi/js exports each icon as
// its own named SVG path string, so only the ones imported below end up
// in the build.
import { h } from 'vue'
import type { IconProps, IconSet } from 'vuetify'
import {
  mdiArrowLeft,
  mdiFastForward15,
  mdiInformationOutline,
  mdiMagnify,
  mdiMicrophoneOutline,
  mdiPause,
  mdiPauseCircleOutline,
  mdiPlay,
  mdiPlayCircleOutline,
  mdiPodcast,
  mdiRewind15,
  mdiSkipNext,
  mdiSkipPrevious,
  mdiSortCalendarAscending,
  mdiSortCalendarDescending
} from '@mdi/js'

const paths: Record<string, string> = {
  'mdi-arrow-left': mdiArrowLeft,
  'mdi-fast-forward-15': mdiFastForward15,
  'mdi-information-outline': mdiInformationOutline,
  'mdi-magnify': mdiMagnify,
  'mdi-microphone-outline': mdiMicrophoneOutline,
  'mdi-pause': mdiPause,
  'mdi-pause-circle-outline': mdiPauseCircleOutline,
  'mdi-play': mdiPlay,
  'mdi-play-circle-outline': mdiPlayCircleOutline,
  'mdi-podcast': mdiPodcast,
  'mdi-rewind-15': mdiRewind15,
  'mdi-skip-next': mdiSkipNext,
  'mdi-skip-previous': mdiSkipPrevious,
  'mdi-sort-calendar-ascending': mdiSortCalendarAscending,
  'mdi-sort-calendar-descending': mdiSortCalendarDescending
}

export const podcastIcons: IconSet = {
  component: (props: IconProps) => {
    const name = typeof props.icon === 'string' ? props.icon : ''
    const path = paths[name]
    if (!path) console.warn(`podcast-icons: unknown icon "${name}"`)
    return h(
      props.tag,
      {},
      {
        default: () => [
          h(
            'svg',
            {
              class: 'v-icon__svg',
              xmlns: 'http://www.w3.org/2000/svg',
              viewBox: '0 0 24 24',
              role: 'img',
              'aria-hidden': 'true'
            },
            [h('path', { d: path ?? '' })]
          )
        ]
      }
    )
  }
}
