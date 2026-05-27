import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/app.css'

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')

