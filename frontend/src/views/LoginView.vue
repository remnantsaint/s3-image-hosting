<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import { loginUser } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)

interface LoginForm {
  username: string
  password: string
}

const form = reactive<LoginForm>({
  username: '',
  password: '',
})

const rules: FormRules<LoginForm> = {
  username: [
    {
      required: true,
      message: '请输入用户名',
      trigger: 'blur',
    },
    {
      min: 3,
      max: 50,
      message: '用户名长度应为3至50个字符',
      trigger: 'blur',
    },
  ],

  password: [
    {
      required: true,
      message: '请输入密码',
      trigger: 'blur',
    },
    {
      min: 8,
      max: 128,
      message: '密码长度应为8至128个字符',
      trigger: 'blur',
    },
  ],
}

function getLoginErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return '登录失败，请稍后重试'
  }

  if (error.response?.status === 401) {
    return '用户名或密码错误'
  }

  if (error.response?.status === 403) {
    return '该账户已被停用'
  }

  if (error.response?.status === 429) {
    const retryAfter =
      error.response.headers['retry-after']

    return retryAfter
      ? `登录失败次数过多，请${retryAfter}秒后重试`
      : '登录失败次数过多，请稍后重试'
  }

  if (error.response?.status === 422) {
    return '登录信息格式不正确'
  }

  return '无法连接服务器，请稍后重试'
}

async function submitLogin() {
  if (!formRef.value) {
    return
  }

  const isValid = await formRef.value
    .validate()
    .catch(() => false)

  if (!isValid) {
    return
  }

  submitting.value = true

  try {
    const tokenResponse = await loginUser({
      username: form.username,
      password: form.password,
    })

    // 同时保存到Pinia和localStorage
    authStore.setAccessToken(
      tokenResponse.access_token,
    )

    ElMessage.success('登录成功')

    // 如果是被登录保护拦截过来的，则返回原页面
    const redirect = route.query.redirect

    if (
      typeof redirect === 'string' &&
      redirect.startsWith('/')
    ) {
      await router.push(redirect)
    } else {
      await router.push('/images')
    }
  } catch (error) {
    ElMessage.error(getLoginErrorMessage(error))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <el-card class="auth-card" shadow="never">
      <template #header>
        <div>
          <h1>欢迎回来</h1>
          <p>登录后管理你上传的图片</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submitLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model.trim="form.username"
            placeholder="请输入用户名"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>

        <el-button
          class="submit-button"
          type="primary"
          native-type="submit"
          :loading="submitting"
        >
          登录
        </el-button>
      </el-form>

      <p class="switch-link">
        还没有账户？
        <RouterLink to="/register">前往注册</RouterLink>
      </p>
    </el-card>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.auth-card {
  width: min(100%, 440px);
  border-radius: 14px;
}

.auth-card h1 {
  margin: 0;
  font-size: 26px;
}

.auth-card p {
  margin: 8px 0 0;
  color: #6b7280;
}

.submit-button {
  width: 100%;
  margin-top: 8px;
}

.switch-link {
  text-align: center;
}

.switch-link a {
  color: #409eff;
}
</style>