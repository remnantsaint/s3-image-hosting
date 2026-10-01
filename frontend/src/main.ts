import './assets/main.css'

// 引入Element Plus及其基础样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// 让所有页面都能使用Element Plus组件
app.use(ElementPlus)

app.mount('#app')