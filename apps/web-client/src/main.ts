import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import { initTheme } from './composables/useTheme'
import './assets/main.css'

// Before mount: the inline script in index.html already set the attribute, and this
// re-applies it from the same rules so the two can never disagree.
initTheme()

createApp(App).use(router).use(i18n).mount('#app')
