import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

// JWT在浏览器localStorage中的键名
export const ACCESS_TOKEN_STORAGE_KEY =
    's3_image_hosting_access_token'

export const useAuthStore = defineStore('auth', () => {
    // 页面刷新后，从localStorage恢复JWT
    const accessToken = ref<string | null>(
        localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY),
    )

    // 是否已经保存JWT
    const isAuthenticated = computed(
        () => accessToken.value !== null,
    )

    function setAccessToken(token: string) {
        accessToken.value = token

        localStorage.setItem(
            ACCESS_TOKEN_STORAGE_KEY,
            token,
        )
    }

    function logout() {
        accessToken.value = null

        localStorage.removeItem(
            ACCESS_TOKEN_STORAGE_KEY,
        )
    }

    return {
        accessToken,
        isAuthenticated,
        setAccessToken,
        logout,
    }
})