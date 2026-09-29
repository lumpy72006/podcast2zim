import dayjs from 'dayjs'

/** Seconds -> "mm:ss" or "h:mm:ss" (used by the audio player clock) */
export const formatClock = (totalSeconds: number): string => {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) totalSeconds = 0
  const s = Math.floor(totalSeconds)
  const hours = Math.floor(s / 3600)
  const minutes = Math.floor((s % 3600) / 60)
  const seconds = s % 60
  const mm = String(minutes).padStart(2, '0')
  const ss = String(seconds).padStart(2, '0')
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`
}

/** Seconds -> human friendly length, always down to the second: "17 min 39 sec",
 * "1 h 05 min 30 sec", "46 sec". '' when unknown */
export const formatDuration = (totalSeconds: number): string => {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return ''
  const s = Math.round(totalSeconds)
  const hours = Math.floor(s / 3600)
  const minutes = Math.floor((s % 3600) / 60)
  const seconds = s % 60

  const parts: string[] = []
  if (hours > 0) parts.push(`${hours} h`)
  if (hours > 0 || minutes > 0) {
    parts.push(hours > 0 ? `${String(minutes).padStart(2, '0')} min` : `${minutes} min`)
  }
  parts.push(`${seconds} sec`)
  return parts.join(' ')
}

/** ISO date -> "Sep 9, 2024". '' when missing or invalid */
export const formatDate = (date: string, format: string = 'MMM D, YYYY'): string => {
  if (!date) return ''
  const parsed = dayjs(date)
  return parsed.isValid() ? parsed.format(format) : ''
}

export const truncateText = (text: string, maxLength: number): string => {
  if (text.length > maxLength) {
    return `${text.slice(0, maxLength)}...`
  }
  return text
}

/**
 * Build a URL relative to index.html for a path stored in the ZIM.
 * Each path segment is percent-encoded because episode ids come from feed
 * GUIDs and can contain characters such as ':' '?' '#' or spaces.
 */
export const assetUrl = (path?: string | null): string | undefined => {
  if (!path) return undefined
  return './' + path.split('/').map(encodeURIComponent).join('/')
}
