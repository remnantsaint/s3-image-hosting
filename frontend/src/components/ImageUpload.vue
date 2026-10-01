<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type {
  UploadFile,
  UploadInstance,
} from 'element-plus'

import {
  uploadImage,
  type ImageResponse,
} from '@/api/images'

// 后续图片列表可以监听这个事件并刷新
const emit = defineEmits<{
  uploaded: [image: ImageResponse]
}>()

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadedImage = ref<ImageResponse | null>(null)

const MAX_IMAGE_SIZE = 10 * 1024 * 1024

const ALLOWED_IMAGE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
]

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function handleFileChange(uploadFile: UploadFile) {
  const file = uploadFile.raw

  if (!file) {
    return
  }

  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    ElMessage.error(
      '只支持JPEG、PNG、GIF和WebP图片',
    )

    uploadRef.value?.clearFiles()
    selectedFile.value = null
    return
  }

  if (file.size > MAX_IMAGE_SIZE) {
    ElMessage.error('图片大小不能超过10 MB')

    uploadRef.value?.clearFiles()
    selectedFile.value = null
    return
  }

  selectedFile.value = file
  uploadedImage.value = null
  uploadProgress.value = 0
}

function getUploadErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return '图片上传失败，请稍后重试'
  }

  const status = error.response?.status

  if (status === 400) {
    return '文件内容与图片类型不匹配'
  }

  if (status === 401) {
    return '登录已过期，请重新登录'
  }

  if (status === 413) {
    return '图片大小不能超过10 MB'
  }

  if (status === 415) {
    return '不支持该图片格式'
  }

  if (status === 429) {
    const retryAfter =
      error.response?.headers['retry-after']

    return retryAfter
      ? `上传过于频繁，请${retryAfter}秒后重试`
      : '上传过于频繁，请稍后重试'
  }

  if (status === 503) {
    return '图片存储服务暂时不可用'
  }

  return '无法连接服务器，请稍后重试'
}

async function submitUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  uploading.value = true
  uploadProgress.value = 0

  try {
    const image = await uploadImage(
      selectedFile.value,
      (percentage) => {
        uploadProgress.value = percentage
      },
    )

    uploadedImage.value = image

    // 通知父页面图片已经上传完成
    emit('uploaded', image)

    ElMessage.success('图片上传成功')

    selectedFile.value = null
    uploadRef.value?.clearFiles()
  } catch (error) {
    ElMessage.error(getUploadErrorMessage(error))
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <section class="upload-card">
    <div class="section-heading">
      <h2>上传图片</h2>
      <span>支持JPEG、PNG、GIF和WebP，最大10 MB</span>
    </div>

    <el-upload
      ref="uploadRef"
      drag
      :auto-upload="false"
      :show-file-list="false"
      :disabled="uploading"
      accept="image/jpeg,image/png,image/gif,image/webp"
      :on-change="handleFileChange"
    >
      <el-icon class="upload-icon">
        <UploadFilled />
      </el-icon>

      <div class="upload-text">
        将图片拖到这里，或
        <em>点击选择</em>
      </div>
    </el-upload>

    <div
      v-if="selectedFile"
      class="selected-file"
    >
      <div>
        <strong>{{ selectedFile.name }}</strong>
        <span>
          {{ formatFileSize(selectedFile.size) }}
        </span>
      </div>

      <el-button
        type="primary"
        :loading="uploading"
        @click="submitUpload"
      >
        开始上传
      </el-button>
    </div>

    <el-progress
      v-if="uploading"
      class="upload-progress"
      :percentage="uploadProgress"
    />

    <el-alert
      v-if="uploadedImage"
      class="upload-result"
      type="success"
      :closable="false"
      show-icon
    >
      <template #title>
        上传成功：{{ uploadedImage.original_filename }}
      </template>

      图片编号：{{ uploadedImage.id }}，
      大小：{{ formatFileSize(uploadedImage.size_bytes) }}
    </el-alert>
  </section>
</template>

<style scoped>
.upload-card {
  max-width: 760px;
  margin-top: 32px;
  padding: 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.section-heading {
  margin-bottom: 20px;
}

.section-heading h2 {
  margin: 0;
  font-size: 18px;
}

.section-heading span {
  display: block;
  margin-top: 6px;
  color: #6b7280;
  font-size: 13px;
}

.upload-icon {
  color: #94a3b8;
  font-size: 48px;
}

.upload-text {
  margin-top: 12px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 20px;
}

.selected-file div {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.selected-file strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-file span {
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.upload-progress,
.upload-result {
  margin-top: 20px;
}

@media (max-width: 640px) {
  .selected-file {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>