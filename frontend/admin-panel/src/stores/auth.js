
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

// Configure Axios Base URL (Should be env var, utilizing proxy in dev)
const API_URL = '/api/admin'

export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem('admin_token') || null)
    const user = ref(JSON.parse(localStorage.getItem('admin_user') || 'null'))
    const router = useRouter()

    const isAuthenticated = computed(() => !!token.value)

    async function login(username, password) {
        try {
            // Check headers/config for CORS if needed, but Vite proxy should handle
            // For production, ensure backend allows origin or serves frontend
            const response = await axios.post(`${API_URL}/login`, { username, password })

            const accessToken = response.data.access_token
            token.value = accessToken

            // Decode token or fetch user? For now just username
            user.value = { username }

            localStorage.setItem('admin_token', accessToken)
            localStorage.setItem('admin_user', JSON.stringify(user.value))

            // Set default header
            axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`

            return true
        } catch (error) {
            console.error('Login failed', error)
            throw error.response?.data?.detail || 'Login failed'
        }
    }

    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('admin_token')
        localStorage.removeItem('admin_user')
        delete axios.defaults.headers.common['Authorization']
        // router.push('/login') // Component triggers push usually
    }

    return { token, user, isAuthenticated, login, logout }
})
