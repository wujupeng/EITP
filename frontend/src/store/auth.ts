import { create } from 'zustand'

interface AuthState {
  tenantToken: string | null
  userId: string | null
  isPlatformAdmin: boolean
  setTenantToken: (token: string | null) => void
  setUserId: (id: string | null) => void
  setPlatformAdmin: (isAdmin: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  tenantToken: null,
  userId: null,
  isPlatformAdmin: false,
  setTenantToken: (token) => set({ tenantToken: token }),
  setUserId: (id) => set({ userId: id }),
  setPlatformAdmin: (isAdmin) => set({ isPlatformAdmin: isAdmin }),
  logout: () => set({ tenantToken: null, userId: null, isPlatformAdmin: false }),
}))