import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
    plugins: [vue(), vueDevTools()],

    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },

    server: {
        proxy: {
            // 开发模式下，浏览器请求/api时由Vite转发给本地Nginx。
            // Nginx会继续把/api请求转发给FastAPI。
            '/api': {
                target: 'http://127.0.0.1:8080',
                changeOrigin: true,
            },
        },
    },
})
