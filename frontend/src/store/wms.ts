import { create } from 'zustand'
import type { WmsTask, WmsTaskStatus } from '@/types/wms'
import { wmsApi } from '@/api/wms'

const TASK_POLL_INTERVAL_MS = 5000

export function generateIdempotencyKey(): string {
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

interface WmsState {
  tasks: WmsTask[]
  tasksLoading: boolean
  tasksError: string | null
  executing: boolean
  pollingTimerId: ReturnType<typeof setInterval> | null

  setTasks: (tasks: WmsTask[]) => void
  loadTasks: (params?: { status?: WmsTaskStatus; assignee_id?: string }) => Promise<void>
  startTaskPolling: (params?: { status?: WmsTaskStatus; assignee_id?: string }) => void
  stopTaskPolling: () => void
  setExecuting: (executing: boolean) => void
  clearError: () => void
}

export const useWmsStore = create<WmsState>((set, get) => ({
  tasks: [],
  tasksLoading: false,
  tasksError: null,
  executing: false,
  pollingTimerId: null,

  setTasks: (tasks) => set({ tasks }),

  loadTasks: async (params) => {
    set({ tasksLoading: true, tasksError: null })
    try {
      const tasks = await wmsApi.tasks.list({
        status: params?.status,
        assignee_id: params?.assignee_id,
        limit: 100,
      })
      set({ tasks, tasksLoading: false })
    } catch (err) {
      set({ tasksError: (err as Error).message, tasksLoading: false })
    }
  },

  startTaskPolling: (params) => {
    get().stopTaskPolling()
    const timerId = setInterval(() => {
      get().loadTasks(params)
    }, TASK_POLL_INTERVAL_MS)
    set({ pollingTimerId: timerId })
    get().loadTasks(params)
  },

  stopTaskPolling: () => {
    const timerId = get().pollingTimerId
    if (timerId !== null) {
      clearInterval(timerId)
      set({ pollingTimerId: null })
    }
  },

  setExecuting: (executing) => set({ executing }),

  clearError: () => set({ tasksError: null }),
}))