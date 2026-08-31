import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message } from 'antd'
import { useAuthStore } from '@/store/auth'

interface EITPErrorResponse {
  error_code: string
  message: string
  details?: Record<string, unknown>
}

const client: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

function generateTraceId(): string {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID()
    }
  } catch {
    // fallthrough
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { tenantToken, accessToken } = useAuthStore.getState()
    if (tenantToken) {
      config.headers['X-Tenant-Token'] = tenantToken
    }
    if (accessToken) {
      config.headers['Authorization'] = `Bearer ${accessToken}`
    }
    config.headers['X-Trace-ID'] = generateTraceId()
    return config
  },
  (error) => Promise.reject(error),
)

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<EITPErrorResponse>) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401 && !error.config?.url?.includes('/auth/login')) {
        useAuthStore.getState().logout()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      if (data?.error_code) {
        message.error(`[${data.error_code}] ${data.message}`)
      } else if (status === 401) {
        message.error('认证失败，请重新登录')
      } else if (status === 403) {
        message.error('无权访问该资源')
      } else {
        message.error(`请求失败: ${error.message}`)
      }
    } else {
      message.error('网络错误，请检查连接')
    }
    return Promise.reject(error)
  },
)

export { client }
export type { EITPErrorResponse }
