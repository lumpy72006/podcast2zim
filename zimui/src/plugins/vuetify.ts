import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import axios from 'axios'
import { createVuetify } from 'vuetify'
import type { Config } from '@/types/Podcast'
import { lighten, luminance, normalizeHex, readableOn } from '@/utils/color-utils'

async function loadVuetify() {
  let primaryColor = '#3f51b5'
  let secondaryColor = '#ffffff'

  // Load primary and secondary colors (taken from the podcast artwork) from config.json
  try {
    const response = await axios.get('./config.json')
    if (response.status === axios.HttpStatusCode.Ok) {
      const config: Config = response.data
      primaryColor = normalizeHex(config.mainColor, primaryColor)
      secondaryColor = normalizeHex(config.secondaryColor, secondaryColor)
    }
  } catch (error) {
    console.error('Error loading config:', error)
  }

  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches

  // A very dark artwork colour is invisible on the dark theme: lighten it there
  const primaryOnDark = luminance(primaryColor) < 0.15 ? lighten(primaryColor, 0.4) : primaryColor
  const secondaryOnDark =
    luminance(secondaryColor) < 0.15 ? lighten(secondaryColor, 0.4) : secondaryColor

  // Light Theme
  const zimuiLight = {
    dark: false,
    colors: {
      background: '#FFFFFF',
      surface: '#FFFFFF',
      primary: primaryColor,
      secondary: secondaryColor,
      'on-primary': readableOn(primaryColor),
      'on-secondary': readableOn(secondaryColor),
      'on-surface': '#000000'
    }
  }

  // Dark Theme
  const zimuiDark = {
    dark: true,
    colors: {
      background: '#121212',
      surface: '#1E1E1E',
      primary: primaryOnDark,
      secondary: secondaryOnDark,
      'on-primary': readableOn(primaryOnDark),
      'on-secondary': readableOn(secondaryOnDark),
      'on-surface': '#FFFFFF'
    }
  }

  return createVuetify({
    theme: {
      defaultTheme: prefersDark ? 'zimuiDark' : 'zimuiLight',
      variations: {
        colors: ['primary', 'secondary'],
        lighten: 2,
        darken: 2
      },
      themes: {
        zimuiLight,
        zimuiDark
      }
    }
  })
}

export default loadVuetify
