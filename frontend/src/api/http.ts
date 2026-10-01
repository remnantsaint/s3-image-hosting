import axios from 'axios'

import { ACCESS_TOKEN_STORAGE_KEY } from '@/stores/auth'

// 创建项目统一使用的HTTP客户端
const http = axios.create({
    baseURL: '/api',
    timeout: 10_000,
    headers: {
        Accept: 'application/json',
    },
})

// 每次发送请求前，自动读取JWT
http.interceptors.request.use((config) => {
    const accessToken = localStorage.getItem(
        ACCESS_TOKEN_STORAGE_KEY,
    )

    if (accessToken) {
        config.headers.set(
            'Authorization',
            `Bearer ${accessToken}`,
        )
    }

    return config
})

export default http