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
// Auto-mount logic
// 1. Dev mode: always mount
// 2. Production: mount immediately if window.TRAITTY_WIDGET_AUTO_INIT is true
// 3. Otherwise, wait for manual call to window.mountTalentChat()
const shouldAutoMount = import.meta.env.MODE === 'development' || window.TRAITTY_WIDGET_CONFIG?.autoInit;

if (shouldAutoMount) {
    // Wrap in timeout to ensure DOM is ready if script is in head
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.mountTalentChat());
    } else {
        window.mountTalentChat();
    }
}
