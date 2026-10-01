import { createRouter, createWebHistory } from 'vue-router'

import { ACCESS_TOKEN_STORAGE_KEY } from '@/stores/auth'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),

    routes: [
        {
            path: '/',
            redirect: '/images',
        },
        {
            path: '/login',
            name: 'login',
            // 懒加载
            component: () => import('../views/LoginView.vue'),
        },
        {
            path: '/register',
            name: 'register',
            component: () => import('../views/RegisterView.vue'),
        },
        {
            path: '/images',
            name: 'images',
            component: () => import('../views/GalleryView.vue'),

            // 表示该页面必须登录
            meta: {
                requiresAuth: true,
            },
        },
    ],
})

// 每次切换页面前执行
router.beforeEach((to) => {
    const accessToken = localStorage.getItem(
        ACCESS_TOKEN_STORAGE_KEY,
    )

    // 未登录时访问受保护页面，跳转登录页
    if (to.meta.requiresAuth && !accessToken) {
        return {
            name: 'login',
            query: {
                redirect: to.fullPath,
            },
        }
    }

    // 已登录时不再显示登录和注册页
    if (
        accessToken &&
        (to.name === 'login' || to.name === 'register')
    ) {
        return {
            name: 'images',
        }
    }
})

export default router