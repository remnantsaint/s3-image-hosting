<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

import {
  getCurrentUser,
  type UserResponse,
} from '@/api/auth'
import ImageList from '@/components/ImageList.vue'
import ImageUpload from '@/components/ImageUpload.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const currentUser = ref<UserResponse | null>(null)
const userLoading = ref(false)

// 描述ImageList通过defineExpose提供的方法
interface ImageListExpose {
  refresh: () => Promise<void>
}

const imageListRef = ref<ImageListExpose | null>(null)

async function loadCurrentUser() {
  userLoading.value = true

  try {
    currentUser.value = await getCurrentUser()
  } catch (error) {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401
    ) {
      authStore.logout()

      ElMessage.warning('登录已过期，请重新登录')

      await router.replace('/login')
      return
    }

    ElMessage.error('无法获取当前用户信息')
  } finally {
    userLoading.value = false
  }
}

// 接收ImageUpload发出的uploaded事件
function handleImageUploaded() {
  // 上传成功后重新加载第一页
  void imageListRef.value?.refresh()
}

async function handleLogout() {
  authStore.logout()
  currentUser.value = null

  ElMessage.success('已退出登录')

  await router.replace('/login')
}

onMounted(() => {
  void loadCurrentUser()
})
</script>

<template>
  <main class="gallery-page">
    <header class="page-header">
      <div>
        <h1>图片管理</h1>
        <p>上传、查看和管理你的图片</p>
      </div>

      <div class="user-area">
        <div
          v-if="currentUser"
          class="user-information"
        >
          <strong>{{ currentUser.username }}</strong>
          <span>{{ currentUser.email }}</span>
        </div>

        <span v-else-if="userLoading">
          正在读取用户信息……
        </span>

        <el-button @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </header>

    <ImageUpload
      @uploaded="handleImageUploaded"
    />

    <ImageList ref="imageListRef" />
  </main>
</template>

<style scoped>
.gallery-page {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.page-header h1 {
  margin: 0;
}

.page-header p {
  margin: 8px 0 0;
  color: #6b7280;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-information {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.user-information span {
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

@media (max-width: 640px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .user-area {
    width: 100%;
    justify-content: space-between;
  }

  .user-information {
    align-items: flex-start;
  }
}
</style>