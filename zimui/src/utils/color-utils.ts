// Small helpers so any artwork colour gives a readable UI

interface Rgb {
  r: number
  g: number
  b: number
}

const expandHex = (hex: string): string | null => {
  const group = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim())?.[1]
  if (!group) return null
  const full = group.length === 3 ? group.replace(/./g, (c) => c + c) : group
  return `#${full.toLowerCase()}`
}

const toRgb = (hex: string): Rgb => {
  const h = hex.slice(1)
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16)
  }
}

/** Normalise "#abc" / "abc" / "#AABBCC" to "#aabbcc"; returns fallback if invalid */
export const normalizeHex = (value: string | null | undefined, fallback: string): string => {
  if (!value) return fallback
  return expandHex(value) ?? fallback
}

const channelLuminance = (channel: number): number => {
  const c = channel / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

/** WCAG relative luminance (0 = black, 1 = white) */
export const luminance = (hex: string): number => {
  const { r, g, b } = toRgb(hex)
  return 0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b)
}

/** Black or white, whichever is more readable on top of `hex` */
export const readableOn = (hex: string): string => (luminance(hex) > 0.4 ? '#000000' : '#FFFFFF')

/** Mix `hex` with white by `amount` (0..1) */
export const lighten = (hex: string, amount: number): string => {
  const { r, g, b } = toRgb(hex)
  const mix = (channel: number) =>
    Math.round(channel + (255 - channel) * amount)
      .toString(16)
      .padStart(2, '0')
  return `#${mix(r)}${mix(g)}${mix(b)}`
}
