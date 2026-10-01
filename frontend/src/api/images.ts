import type { AxiosProgressEvent } from 'axios'

import http from './http'

// 上传成功后FastAPI返回的图片信息
export interface ImageResponse {
    id: number
    owner_id: number
    object_key: string
    original_filename: string
    content_type: string
    size_bytes: number
    created_at: string
}

// 上传图片
export async function uploadImage(
    file: File,
    onProgress?: (percentage: number) => void,
): Promise<ImageResponse> {
    const formData = new FormData()

    // 后端接口要求字段名称为file
    formData.append('file', file, file.name)

    const response = await http.post<ImageResponse>(
        '/images',
        formData,
        {
            onUploadProgress: (
                progressEvent: AxiosProgressEvent,
            ) => {
                if (!progressEvent.total || !onProgress) {
                    return
                }

                const percentage = Math.round(
                    (progressEvent.loaded * 100) /
                    progressEvent.total,
                )

                onProgress(percentage)
            },
        },
    )

    return response.data
}

// 图片列表中的单条数据
export interface ImageListItem {
    id: number
    original_filename: string
    content_type: string
    size_bytes: number
    created_at: string
    url: string
    // 固定分享链接；null表示尚未分享
    share_url: string | null
}

// 分页图片列表
export interface ImageListResponse {
    total: number
    page: number
    page_size: number
    items: ImageListItem[]
}

// 查询当前用户的图片
export async function listImages(
    page: number,
    pageSize: number,
): Promise<ImageListResponse> {
    const response = await http.get<ImageListResponse>(
        '/images',
        {
            params: {
                page,
                page_size: pageSize,
            },
        },
    )

    return response.data
}


// 创建固定分享链接后的响应
export interface ImageShareResponse {
    id: number
    share_url: string
}

// 为指定图片创建固定分享链接
export async function createImageShare(
    imageId: number,
): Promise<ImageShareResponse> {
    const response = await http.post<ImageShareResponse>(
        `/images/${imageId}/share`,
    )

    return response.data
}

// 取消固定分享，但不删除原图片
export async function cancelImageShare(
    imageId: number,
): Promise<void> {
    await http.delete(`/images/${imageId}/share`)
}


// 删除图片
export async function deleteImage(
    imageId: number,
): Promise<void> {
    await http.delete(`/images/${imageId}`)
}