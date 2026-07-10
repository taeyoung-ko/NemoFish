import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './assets/design-tokens.css'   // 전역 AWS 스타일 토큰 + 리셋 (DESIGN.md)

const app = createApp(App)

app.use(router)
app.use(i18n)

app.mount('#app')
