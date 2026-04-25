import { createApp } from 'vue'
import './style.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import App from './App.vue'
import { createPinia } from 'pinia'
import { router } from '@/router'

createApp(App).use(createPinia()).use(router).mount('#app')
