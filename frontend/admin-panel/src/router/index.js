
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: () => import('../views/LoginView.vue'),
            meta: { layout: 'auth' }
        },
        {
            path: '/',
            redirect: '/dashboard'
        },
        {
            path: '/dashboard',
            name: 'dashboard',
            component: () => import('../views/DashboardView.vue'),
            meta: { requiresAuth: true, title: 'Analytics' }
        },
        {
            path: '/sessions',
            name: 'sessions',
            component: () => import('../views/SessionListView.vue'), // Placeholder
            meta: { requiresAuth: true, title: 'Session Management' }
        },
        {
            path: '/sessions/:id',
            name: 'session-detail',
            component: () => import('../views/SessionDetailView.vue'), // Placeholder
            meta: { requiresAuth: true, title: 'Session Detail' }
        }
    ]
})

router.beforeEach(async (to, from, next) => {
    // We need to import store inside guard to avoid Pinia init issues
    const authStore = useAuthStore()

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next('/login')
    } else if (to.path === '/login' && authStore.isAuthenticated) {
        next('/dashboard')
    } else {
        next()
    }
})

export default router
