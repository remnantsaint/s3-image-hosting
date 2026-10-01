<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import { registerUser } from '@/api/auth'

// 注册成功后用于跳转登录页面
const router = useRouter()

// 获取Element Plus表单实例
const formRef = ref<FormInstance>()

// 控制注册按钮的加载状态，防止重复提交
const submitting = ref(false)

// 页面表单比后端多一个确认密码字段
interface RegisterForm {
  username: string
  email: string
  password: string
  confirmPassword: string
}

const form = reactive<RegisterForm>({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

// 表单校验规则
const rules: FormRules<RegisterForm> = {
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
    {
      pattern: /^[A-Za-z0-9_]+$/,
      message: '用户名只能包含英文字母、数字和下划线',
      trigger: 'blur',
    },
  ],

  email: [
    {
      required: true,
      message: '请输入邮箱',
      trigger: 'blur',
    },
    {
      type: 'email',
      message: '请输入正确的邮箱地址',
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

  confirmPassword: [
    {
      required: true,
      message: '请再次输入密码',
      trigger: 'blur',
    },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
          return
        }

        callback()
      },
      trigger: 'blur',
    },
  ],
}

// 将后端错误转换成适合页面显示的中文提示
function getRegisterErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return '注册失败，请稍后重试'
  }

  const detail = error.response?.data?.detail

  if (detail === 'Username is already registered') {
    return '该用户名已经被注册'
  }

  if (detail === 'Email is already registered') {
    return '该邮箱已经被注册'
  }

  if (detail === 'Username or email is already registered') {
    return '用户名或邮箱已经被注册'
  }

  if (error.response?.status === 422) {
    return '注册信息格式不正确'
  }

  return '无法连接服务器，请稍后重试'
}

async function submitRegister() {
  if (!formRef.value) {
    return
  }

  // 先执行浏览器端表单校验
  const isValid = await formRef.value
    .validate()
    .catch(() => false)

  if (!isValid) {
    return
  }

  submitting.value = true

  try {
    await registerUser({
      username: form.username,
      email: form.email,
      password: form.password,
    })

    ElMessage.success('注册成功，请登录')

    // 注册完成后进入登录页面
    await router.push('/login')
  } catch (error) {
    ElMessage.error(getRegisterErrorMessage(error))
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
          <h1>创建账户</h1>
          <p>注册后即可上传和管理图片</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submitRegister"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model.trim="form.username"
            placeholder="3至50个字符"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model.trim="form.email"
            placeholder="name@example.com"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="至少8个字符"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="再次输入密码"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>

        <el-button
          class="submit-button"
          type="primary"
          native-type="submit"
          :loading="submitting"
        >
          注册
        </el-button>
      </el-form>

      <p class="switch-link">
        已有账户？
        <RouterLink to="/login">前往登录</RouterLink>
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