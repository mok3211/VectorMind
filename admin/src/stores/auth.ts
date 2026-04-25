import { defineStore } from 'pinia'
import { api } from '@/lib/api'

type Me = { id: number; email: string; is_admin: boolean }

export const useAuthStore = defineStore('auth', {
  state: () => ({
    me: null as Me | null,
    loading: false
  }),
  actions: {
    async login(email: string, password: string) {
      this.loading = true
      try {
        const { data } = await api.post('/auth/login', { email, password })
        localStorage.setItem('access_token', data.access_token)
        await this.fetchMe()
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      const { data } = await api.get('/auth/me')
      this.me = data
    },
    logout() {
      localStorage.removeItem('access_token')
      this.me = null
    }
  }
})

