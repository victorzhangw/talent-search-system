
<template>
  <div class="login-wrapper">
    <div class="login-card">
        <div class="brand">
            <div class="logo-icon">P</div>
            <h1>Admin Portal</h1>
        </div>
        
        <p class="subtitle">Sign in to manage the chatbot system</p>

        <form @submit.prevent="handleLogin" class="login-form">
            <BaseInput 
                v-model="username" 
                label="Username" 
                placeholder="Enter admin username"
                required
            />
            
            <BaseInput 
                v-model="password" 
                label="Password" 
                type="password" 
                placeholder="••••••••"
                required
            />

            <div v-if="error" class="error-msg">
                {{ error }}
            </div>

            <BaseButton type="submit" :loading="isLoading" class="w-full">
                Sign In
            </BaseButton>
        </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import BaseInput from '../components/base/BaseInput.vue'
import BaseButton from '../components/base/BaseButton.vue'

const username = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)

const authStore = useAuthStore()
const router = useRouter()

const handleLogin = async () => {
    error.value = ''
    isLoading.value = true
    try {
        await authStore.login(username.value, password.value)
        router.push('/dashboard')
    } catch (e) {
        error.value = typeof e === 'string' ? e : 'Authentication failed'
    } finally {
        isLoading.value = false
    }
}
</script>

<style lang="scss" scoped>
.login-wrapper {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: $bg-body;
}

.login-card {
    background: white;
    padding: 3rem;
    border-radius: $border-radius;
    box-shadow: $shadow-md;
    width: 100%;
    max-width: 420px;
    text-align: center;

    .brand {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.5rem;

        .logo-icon {
            width: 48px;
            height: 48px;
            background: $primary-color;
            color: white;
            font-size: 1.5rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
        }

        h1 {
            font-size: 1.5rem;
            color: $text-main;
            margin: 0;
        }
    }

    .subtitle {
        color: $text-muted;
        margin-bottom: 2rem;
        font-size: 0.95rem;
    }

    .login-form {
        text-align: left;
    }

    .error-msg {
        color: $danger-color;
        font-size: 0.9rem;
        margin-bottom: 1rem;
        text-align: center;
        background: rgba($danger-color, 0.1);
        padding: 0.5rem;
        border-radius: 4px;
    }

    .w-full {
        width: 100%;
        margin-top: 1rem;
    }
}
</style>
