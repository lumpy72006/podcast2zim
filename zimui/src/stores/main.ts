import { defineStore } from 'pinia'
import axios, { AxiosError } from 'axios'
import type { Episode, Podcast } from '@/types/Podcast'

export type RootState = {
  podcast: Podcast | null
  isLoading: boolean
  errorMessage: string
  errorDetails: string
}

export const useMainStore = defineStore('main', {
  state: () =>
    ({
      podcast: null,
      isLoading: false,
      errorMessage: '',
      errorDetails: ''
    }) as RootState,
  actions: {
    /** Load podcast.json once; later calls reuse the loaded data */
    async fetchPodcast(force: boolean = false) {
      if (this.podcast && !force) return this.podcast
      this.isLoading = true
      this.errorMessage = ''
      this.errorDetails = ''

      return axios.get('./podcast.json').then(
        (response) => {
          this.isLoading = false
          this.checkResponseObject(response.data, 'Podcast not found.')
          this.podcast = response.data as Podcast
          return this.podcast
        },
        (error) => {
          this.isLoading = false
          this.podcast = null
          this.errorMessage = 'Failed to load podcast data.'
          if (error instanceof AxiosError) {
            this.handleAxiosError(error)
          }
        }
      )
    },
    async fetchEpisode(id: string) {
      this.isLoading = true
      this.errorMessage = ''
      this.errorDetails = ''

      return axios.get(`./episodes/${encodeURIComponent(id)}.json`).then(
        (response) => {
          this.isLoading = false
          this.checkResponseObject(response.data, 'Episode not found.')
          return response.data as Episode
        },
        (error) => {
          this.isLoading = false
          this.errorMessage = 'Failed to load episode data.'
          if (error instanceof AxiosError) {
            this.handleAxiosError(error)
          }
        }
      )
    },
    checkResponseObject(response: unknown, msg: string = '') {
      if (response === null || typeof response !== 'object') {
        if (msg !== '') {
          this.errorDetails = msg
        }
        throw new Error('Invalid response object.')
      }
    },
    handleAxiosError(error: AxiosError<object>) {
      if (axios.isAxiosError(error) && error.response) {
        const status = error.response.status
        switch (status) {
          case 400:
            this.errorDetails =
              'HTTP 400: Bad Request. The server could not understand the request.'
            break
          case 404:
            this.errorDetails =
              'HTTP 404: Not Found. The requested resource could not be found on the server.'
            break
          case 500:
            this.errorDetails =
              'HTTP 500: Internal Server Error. The server encountered an unexpected error.'
            break
        }
      }
    },
    setErrorMessage(message: string) {
      this.errorMessage = message
    }
  }
})
