import http from './http'

// 描述FastAPI的/health接口返回的数据结构
export interface HealthResponse {
    status: string
    service: string
    environment: string
}

// 请求后端健康检查，并只返回响应中的JSON数据
export async function getApplicationHealth(): Promise<HealthResponse> {
    const response = await http.get<HealthResponse>('/health')

    return response.data
}