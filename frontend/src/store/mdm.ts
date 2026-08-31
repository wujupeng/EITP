import { create } from 'zustand'
import type {
  GroupProduct,
  EnterpriseProduct,
  GovernanceRequest,
  NegativePolicyConfig,
  MasterDataAudit,
} from '@/api/mdm/types'

interface MdmState {
  groupProducts: GroupProduct[]
  currentGroupProduct: GroupProduct | null
  enterpriseProducts: EnterpriseProduct[]
  currentEnterpriseProduct: EnterpriseProduct | null
  governanceRequests: GovernanceRequest[]
  negativePolicyConfig: NegativePolicyConfig | null
  auditLogs: MasterDataAudit[]
  loading: boolean
  error: string | null

  setGroupProducts: (products: GroupProduct[]) => void
  setCurrentGroupProduct: (product: GroupProduct | null) => void
  setEnterpriseProducts: (products: EnterpriseProduct[]) => void
  setCurrentEnterpriseProduct: (product: EnterpriseProduct | null) => void
  setGovernanceRequests: (requests: GovernanceRequest[]) => void
  setNegativePolicyConfig: (config: NegativePolicyConfig | null) => void
  setAuditLogs: (logs: MasterDataAudit[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useMdmStore = create<MdmState>((set) => ({
  groupProducts: [],
  currentGroupProduct: null,
  enterpriseProducts: [],
  currentEnterpriseProduct: null,
  governanceRequests: [],
  negativePolicyConfig: null,
  auditLogs: [],
  loading: false,
  error: null,

  setGroupProducts: (products) => set({ groupProducts: products }),
  setCurrentGroupProduct: (product) => set({ currentGroupProduct: product }),
  setEnterpriseProducts: (products) => set({ enterpriseProducts: products }),
  setCurrentEnterpriseProduct: (product) => set({ currentEnterpriseProduct: product }),
  setGovernanceRequests: (requests) => set({ governanceRequests: requests }),
  setNegativePolicyConfig: (config) => set({ negativePolicyConfig: config }),
  setAuditLogs: (logs) => set({ auditLogs: logs }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))