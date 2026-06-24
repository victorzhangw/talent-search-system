<template>
  <div class="login-view">
    <div class="logo-section">
      <!-- Icon: Psychology/AI -->
      <svg class="material-icon logo-icon" viewBox="0 0 24 24"><path d="M6 5.5v13h12v-13H6zm12-1.5c.83 0 1.5.67 1.5 1.5v13c0 .83-.67 1.5-1.5 1.5H6c-.83 0-1.5-.67-1.5-1.5v-13c0-.83.67-1.5 1.5-1.5h12z M13 8.5h-2v2H9v2h2v2h2v-2h2v-2h-2v-2z" fill-rule="evenodd"/><path d="M0 0h24v24H0z" fill="none"/><circle cx="14.5" cy="18.5" r="1"/> <circle cx="9.5" cy="5.5" r="1"/> <circle cx="5.5" cy="13.5" r="1"/> <circle cx="18.5" cy="10.5" r="1"/></svg>
      <h2>歡迎使用 Talent Chat</h2>
      <p>請輸入您的原系統 Email 以進行驗證</p>
    </div>

    <div class="form-section">
        <label>Email Address</label>
        <div class="input-wrapper">
             <svg class="material-icon input-icon" viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
             <input 
                v-model="email" 
                type="email" 
                placeholder="name@company.com" 
                @keydown.enter="handleLogin"
            />
        </div>
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button class="login-btn" @click="handleLogin" :disabled="isLoading">
            <span v-if="!isLoading">驗證並登入</span>
            <span v-else>處理中...</span>
        </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  serverRoot: {
    type: String,
    default: 'http://localhost:5000'
  },
  initialError: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['login-success'])

const email = ref('')
const errorMsg = ref(props.initialError)
const isLoading = ref(false)

const handleLogin = async () => {
    if (!email.value) {
        errorMsg.value = '請輸入 Email'
        return
    }
    
    isLoading.value = true
    errorMsg.value = ''

    try {
        // Use dynamic server root
        const res = await fetch(`${props.serverRoot}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email.value })
        })

        if (!res.ok) {
            throw new Error('驗證失敗')
        }

        const resp = await res.json()
        if (resp.success && resp.data?.token) {
            emit('login-success', resp.data)
        } else {
            throw new Error('無法取得授權，請稍後再試')
        }
    } catch (e) {
        errorMsg.value = e.message?.includes('fetch') ? '無法連線至伺服器，請確認網路後重試' : (e.message || '發生錯誤，請稍後再試')
    } finally {
        isLoading.value = false
    }
}
</script>

<style lang="scss" scoped>
.login-view {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    padding: 2rem;
    color: var(--glass-text-primary);
}

.logo-section {
    text-align: center;
    margin-bottom: 3rem;
    
    .logo-icon {
        width: 64px;
        height: 64px;
        fill: var(--primary-color);
        margin-bottom: 1rem;
    }
    
    h2 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    p { margin: 0.5rem 0 0; color: var(--glass-text-secondary); }
}

.form-section {
    width: 100%;
    max-width: 320px;
    
    label {
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
        display: block;
        color: var(--glass-text-secondary);
    }
    
    .input-wrapper {
        position: relative;
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        
        .input-icon {
            position: absolute;
            left: 10px;
            width: 20px;
            height: 20px;
            fill: var(--glass-text-secondary);
            opacity: 0.7;
        }
        
        input {
            width: 100%;
            height: 48px;
            padding: 0 1rem 0 2.5rem;
            background: rgba(127, 127, 127, 0.1);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            color: var(--glass-text-primary);
            font-size: 1rem;
            outline: none;
            transition: all 0.2s;
            
            &:focus {
                border-color: var(--primary-color);
                background: rgba(127, 127, 127, 0.15);
            }
        }
    }
    
    .error-msg {
        color: #ef4444;
        font-size: 0.85rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .login-btn {
        width: 100%;
        height: 48px;
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
        
        &:hover:not(:disabled) {
            background: var(--primary-hover);
        }
        
        &:disabled {
            opacity: 0.6;
            cursor: wait;
        }
    }
}
</style>
