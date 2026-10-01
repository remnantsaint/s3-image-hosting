<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  ElMessage,
  ElMessageBox,
} from 'element-plus'
import {
  Delete as DeleteIcon,
  Link as LinkIcon,
} from '@element-plus/icons-vue'

import {
  cancelImageShare,
  createImageShare,
  deleteImage,
  listImages,
  type ImageListItem,
} from '@/api/images'

const images = ref<ImageListItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 8
const loading = ref(false)

// 记录当前正在操作的图片，防止按钮被重复点击
const creatingShareImageId = ref<number | null>(null)
const copyingImageId = ref<number | null>(null)
const cancellingShareImageId = ref<number | null>(null)
const deletingImageId = ref<number | null>(null)

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatCreatedAt(value: string): string {
  const containsTimezone =
    value.endsWith('Z') ||
    /[+-]\d{2}:\d{2}$/.test(value)

  const normalizedValue = containsTimezone
    ? value
    : `${value}Z`

  return new Date(normalizedValue).toLocaleString(
    'zh-CN',
  )
}

function selectShareLink(event: FocusEvent) {
  const target = event.target

  // 点击链接框时自动选中完整地址，
  // 即使浏览器禁止自动访问剪贴板，也可以按Ctrl+C复制。
  if (target instanceof HTMLInputElement) {
    target.select()
  }
}

async function loadImages() {
  loading.value = true

  try {
    const result = await listImages(
      currentPage.value,
      pageSize,
    )

    images.value = result.items
    total.value = result.total
  } catch {
    ElMessage.error('获取图片列表失败')
  } finally {
    loading.value = false
  }
}

async function handlePageChange(page: number) {
  currentPage.value = page
  await loadImages()
}


async function createShare(image: ImageListItem) {
  creatingShareImageId.value = image.id

  try {
    // 请求后端创建固定分享链接
    const result = await createImageShare(image.id)

    // 直接更新当前卡片，不必重新请求整个列表
    image.share_url = result.share_url

    try {
      // 创建成功后顺便复制到系统剪贴板
      await navigator.clipboard.writeText(
        result.share_url,
      )

      ElMessage.success(
        '固定分享链接已创建并复制',
      )
    } catch {
      ElMessage.warning(
        '链接已创建，请在卡片中的链接框内手动复制',
      )
    }
  } catch {
    ElMessage.error('创建分享链接失败')
  } finally {
    creatingShareImageId.value = null
  }
}

async function copyShareUrl(image: ImageListItem) {
  if (!image.share_url) {
    return
  }

  copyingImageId.value = image.id

  try {
    await navigator.clipboard.writeText(
      image.share_url,
    )

    ElMessage.success('固定分享链接已复制')
  } catch {
    ElMessage.warning(
      '浏览器未允许自动复制，请在链接框内手动复制',
    )
  } finally {
    copyingImageId.value = null
  }
}

async function cancelShare(image: ImageListItem) {
  try {
    await ElMessageBox.confirm(
      '取消分享后，原固定链接将立即失效，是否继续？',
      '取消分享',
      {
        confirmButtonText: '确认取消',
        cancelButtonText: '保留分享',
        type: 'warning',
      },
    )
  } catch {
    // 用户关闭确认框时不进行任何操作
    return
  }

  cancellingShareImageId.value = image.id

  try {
    await cancelImageShare(image.id)

    // 后端已经清除分享码，前端同步更新状态
    image.share_url = null

    ElMessage.success('已取消分享')
  } catch {
    ElMessage.error('取消分享失败，请稍后重试')
  } finally {
    cancellingShareImageId.value = null
  }
}

async function removeImage(image: ImageListItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除“${image.original_filename}”吗？删除后无法恢复。`,
      '删除图片',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    // 用户点击取消时，直接结束函数
    return
  }

  deletingImageId.value = image.id

  try {
    await deleteImage(image.id)

    ElMessage.success('图片已删除')

    /*
     * 如果当前页只有这一张图片，并且不是第一页，
     * 删除后退回上一页，避免显示空白分页。
     */
    if (
      images.value.length === 1 &&
      currentPage.value > 1
    ) {
      currentPage.value -= 1
    }

    await loadImages()
  } catch {
    ElMessage.error('删除图片失败，请稍后重试')
  } finally {
    deletingImageId.value = null
  }
}

// 上传成功后由父页面调用
async function refresh() {
  currentPage.value = 1
  await loadImages()
}

defineExpose({
  refresh,
})

onMounted(() => {
  void loadImages()
})
</script>

<template>
  <section
    v-loading="loading"
    class="image-list-card"
  >
    <div class="section-heading">
      <div>
        <h2>我的图片</h2>
        <span>共{{ total }}张图片</span>
      </div>

      <el-button
        :loading="loading"
        @click="loadImages"
      >
        刷新
      </el-button>
    </div>

    <el-empty
      v-if="!loading && images.length === 0"
      description="还没有上传图片"
    />

    <div
      v-else
      class="image-grid"
    >
      <article
        v-for="image in images"
        :key="image.id"
        class="image-card"
      >
        <el-image
          class="image-preview"
          :src="image.url"
          :preview-src-list="[image.url]"
          :initial-index="0"
          fit="cover"
          lazy
          preview-teleported
        >
          <template #error>
            <div class="image-error">
              图片加载失败
            </div>
          </template>
        </el-image>

        <div class="image-information">
          <strong :title="image.original_filename">
            {{ image.original_filename }}
          </strong>

          <span>
            {{ formatFileSize(image.size_bytes) }}
          </span>

          <span>
            {{ formatCreatedAt(image.created_at) }}
          </span>

          <div
            v-if="image.share_url"
            class="share-link-field"
          >
            <label :for="`share-link-${image.id}`">
              固定分享链接
            </label>

            <input
              :id="`share-link-${image.id}`"
              :value="image.share_url"
              type="text"
              readonly
              @focus="selectShareLink"
            >
          </div>

          <div class="image-actions">
            <el-button
                v-if="!image.share_url"
                link
                type="primary"
                :icon="LinkIcon"
                :loading="creatingShareImageId === image.id"
                @click="createShare(image)"
            >
                创建分享
            </el-button>

            <template v-else>
                <el-button
                link
                type="primary"
                :icon="LinkIcon"
                :loading="copyingImageId === image.id"
                @click="copyShareUrl(image)"
                >
                复制分享链接
                </el-button>

                <el-button
                link
                type="warning"
                :loading="cancellingShareImageId === image.id"
                @click="cancelShare(image)"
                >
                取消分享
                </el-button>
            </template>

            <el-button
                class="delete-button"
                link
                type="danger"
                :icon="DeleteIcon"
                :loading="deletingImageId === image.id"
                @click="removeImage(image)"
            >
                删除
            </el-button>
            </div>
        </div>
      </article>
    </div>

    <el-pagination
      v-if="total > pageSize"
      class="pagination"
      background
      layout="prev, pager, next, total"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @current-change="handlePageChange"
    />
  </section>
</template>

<style scoped>
.image-list-card {
  min-height: 240px;
  margin-top: 32px;
  padding: 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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

.image-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fill,
    minmax(200px, 1fr)
  );
  gap: 20px;
}

.image-card {
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}

.image-preview {
  width: 100%;
  height: 160px;
  display: block;
  background: #f1f5f9;
}

.image-error {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
}

.image-information {
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 14px;
}

.image-information strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-information > span {
  margin-top: 5px;
  color: #6b7280;
  font-size: 12px;
}

.share-link-field {
  margin-top: 10px;
}

.share-link-field label {
  display: block;
  margin-bottom: 5px;
  color: #6b7280;
  font-size: 12px;
}

.share-link-field input {
  width: 100%;
  box-sizing: border-box;
  padding: 7px 9px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #dbe3ee;
  border-radius: 6px;
  font-size: 12px;
  cursor: text;
}

.share-link-field input:focus {
  border-color: #409eff;
  outline: none;
}

.image-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.image-actions :deep(.el-button) {
  margin-left: 0;
}

.delete-button {
  margin-left: auto !important;
}

.pagination {
  margin-top: 24px;
  justify-content: center;
}

@media (max-width: 640px) {
  .image-list-card {
    padding: 16px;
  }

  .image-grid {
    grid-template-columns: 1fr;
  }
}
</style>
