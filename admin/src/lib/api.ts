import axios from 'axios'

export const api = axios.create({
  baseURL: '/',
  timeout: 180_000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  // 便于定位前端是否真的发起了请求
  // eslint-disable-next-line no-console
  console.log('[api]', (config.method || 'GET').toUpperCase(), config.url, config.data ?? '')
  return config
})
