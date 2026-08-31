import { create } from 'zustand'

interface AuthState {
  tenantToken: string | null
  accessToken: string | null
  refreshToken: string | null
  userId: string | null
  username: string | null
  tenantId: string | null
  isPlatformAdmin: boolean
  isTenantAdmin: boolean
  isAuthenticated: boolean
  setTenantToken: (token: string | null) => void
  setAuth: (data: {
    access_token: string
    refresh_token: string
    user_id: string
    username: string
    tenant_id: string
    is_platform_admin: boolean
    is_tenant_admin: boolean
  }) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  tenantToken: localStorage.getItem('tenantToken') || '00000000-0000-0000-0000-000000000001',
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
  userId: localStorage.getItem('userId'),
  username: localStorage.getItem('username'),
  tenantId: localStorage.getItem('tenantId'),
  isPlatformAdmin: localStorage.getItem('isPlatformAdmin') === 'true',
  isTenantAdmin: localStorage.getItem('isTenantAdmin') === 'true',
  isAuthenticated: !!localStorage.getItem('accessToken'),
  setTenantToken: (token) => {
    if (token) localStorage.setItem('tenantToken', token)
    else localStorage.removeItem('tenantToken')
    set({ tenantToken: token })
  },
  setAuth: (data) => {
    localStorage.setItem('accessToken', data.access_token)
    localStorage.setItem('refreshToken', data.refresh_token)
    localStorage.setItem('userId', data.user_id)
    localStorage.setItem('username', data.username)
    localStorage.setItem('tenantId', data.tenant_id)
    localStorage.setItem('isPlatformAdmin', String(data.is_platform_admin))
    localStorage.setItem('isTenantAdmin', String(data.is_tenant_admin))
    set({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      userId: data.user_id,
      username: data.username,
      tenantId: data.tenant_id,
      isPlatformAdmin: data.is_platform_admin,
      isTenantAdmin: data.is_tenant_admin,
      tenantToken: data.tenant_id,
      isAuthenticated: true,
    })
  },
  logout: () => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('userId')
    localStorage.removeItem('username')
    localStorage.removeItem('tenantId')
    localStorage.removeItem('isPlatformAdmin')
    localStorage.removeItem('isTenantAdmin')
    set({
      accessToken: null,
      refreshToken: null,
      userId: null,
      username: null,
      tenantId: null,
      isPlatformAdmin: false,
      isTenantAdmin: false,
      isAuthenticated: false,
    })
  },
}))
