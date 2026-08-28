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

client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const tenantToken = useAuthStore.getState().tenantToken
    if (tenantToken) {
      config.headers['X-Tenant-Token'] = tenantToken
    }
    const traceId = crypto.randomUUID()
    config.headers['X-Trace-ID'] = traceId
    return config
  },
  (error) => Promise.reject(error),
)

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<EITPErrorResponse>) => {
    if (error.response) {
      const { status, data } = error.response
      if (data?.error_code) {
        message.error(`[${data.error_code}] ${data.message}`)
      } else if (status === 401) {
        message.error('租户令牌无效或缺失，请重新登录')
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