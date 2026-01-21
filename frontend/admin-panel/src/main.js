import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './assets/styles/main.scss'

import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Axios Interceptor for 401
import axios from 'axios'
import { useAuthStore } from './stores/auth'

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
