import { createApp } from 'vue'
import './styles/global.scss'
import App from './App.vue'

// Custom mount function to allow injection into specific container
// or Shadow DOM
window.mountTalentChat = (containerId = 'talent-chat-root') => {
    let container = document.getElementById(containerId)
    if (!container) {
        container = document.createElement('div')
        container.id = containerId
        document.body.appendChild(container)
    }

    createApp(App).mount(container)
}

// Auto-mount if in dev mode
if (import.meta.env.MODE === 'development') {
    window.mountTalentChat()
}
