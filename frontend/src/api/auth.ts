import http from './http'

// 注册请求数据
export interface RegisterRequest {
    username: string
    email: string
    password: string
}

// 登录请求数据
export interface LoginRequest {
    username: string
    password: string
}

// 登录成功后返回的JWT
export interface TokenResponse {
    access_token: string
    token_type: string
}

// 用户信息
export interface UserResponse {
    id: number
    username: string
    email: string
    is_active: boolean
    created_at: string
    updated_at: string
}

// 注册用户
export async function registerUser(
    data: RegisterRequest,
): Promise<UserResponse> {
    const response = await http.post<UserResponse>(
        '/auth/register',
        data,
    )

    return response.data
}

// 登录并获取JWT
export async function loginUser(
    data: LoginRequest,
): Promise<TokenResponse> {
    const response = await http.post<TokenResponse>(
        '/auth/login',
        data,
    )

    return response.data
}

// 获取当前JWT对应的用户信息
export async function getCurrentUser(): Promise<UserResponse> {
    const response = await http.get<UserResponse>(
        '/users/me',
    )

    return response.data
}