import { create } from 'zustand'

interface SecState {
  batchId: string | null
  batchProgress: { total_items: number; passed: number; failed: number; unexecutable: number; status: string } | null
  currentReport: Record<string, unknown> | null
  currentCertificate: Record<string, unknown> | null
  config: Record<string, unknown> | null
  auditRecords: unknown[]
  accessRequests: unknown[]
  redisScanResult: Record<string, unknown> | null
  attackChainResult: Record<string, unknown> | null
  setBatchId: (id: string | null) => void
  setBatchProgress: (p: SecState['batchProgress']) => void
  setCurrentReport: (r: Record<string, unknown> | null) => void
  setCurrentCertificate: (c: Record<string, unknown> | null) => void
  setConfig: (c: Record<string, unknown> | null) => void
  setAuditRecords: (r: unknown[]) => void
  setAccessRequests: (r: unknown[]) => void
  setRedisScanResult: (r: Record<string, unknown> | null) => void
  setAttackChainResult: (r: Record<string, unknown> | null) => void
}

export const useSecStore = create<SecState>((set) => ({
  batchId: null,
  batchProgress: null,
  currentReport: null,
  currentCertificate: null,
  config: null,
  auditRecords: [],
  accessRequests: [],
  redisScanResult: null,
  attackChainResult: null,
  setBatchId: (id) => set({ batchId: id }),
  setBatchProgress: (p) => set({ batchProgress: p }),
  setCurrentReport: (r) => set({ currentReport: r }),
  setCurrentCertificate: (c) => set({ currentCertificate: c }),
  setConfig: (c) => set({ config: c }),
  setAuditRecords: (r) => set({ auditRecords: r }),
  setAccessRequests: (r) => set({ accessRequests: r }),
  setRedisScanResult: (r) => set({ redisScanResult: r }),
  setAttackChainResult: (r) => set({ attackChainResult: r }),
}))