import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './assets/styles/main.scss'

import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Axios Configuration
import axios from 'axios'
import { useAuthStore } from './stores/auth'

// 1. Load config from window (Runtime) or Env (Build time)
const config = window.ADMIN_PANEL_CONFIG || {}
const apiBaseUrl = config.apiBaseUrl || import.meta.env.VITE_API_BASE_URL || ''

if (apiBaseUrl) {
    axios.defaults.baseURL = apiBaseUrl
    console.log('[AdminPanel] Using API Base URL:', apiBaseUrl)
}

// 2. Interceptor for 401
axios.interceptors.response.use(
    response => response,
    error => {
        if (error.response && error.response.status === 401) {
            // "Token is missing!" or invalid
            const auth = useAuthStore()
            auth.logout()

            // Show alert as requested
            alert("您的登入工作階段已過期或無效，請重新登入。")

            router.push('/login')
        }
        return Promise.reject(error)
    }
)

app.mount('#app')
