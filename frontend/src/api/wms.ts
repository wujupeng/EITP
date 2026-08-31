import { client } from './client'
import type {
  AssignTaskRequest,
  CreateAreaRequest,
  CreateBinRequest,
  CreateEquipmentRequest,
  CreateLocationRequest,
  CreateTaskRequest,
  CreateWarehouseRequest,
  CreateZoneRequest,
  IdResult,
  InventoryPosition,
  InventoryPositionAggregate,
  Location,
  PickingExecuteRequest,
  PutawayExecuteRequest,
  ReceivingExecuteRequest,
  ReconcileDiff,
  ReconcileResolveRequest,
  ShippingExecuteRequest,
  SpaceTreeResponse,
  TaskResult,
  ToggleStatusRequest,
  TransferApproveRequest,
  TransferExecuteRequest,
  WmsTask,
  Zone,
} from '@/types/wms'

export const wmsApi = {
  space: {
    async createWarehouse(payload: CreateWarehouseRequest): Promise<IdResult> {
      const { data } = await client.post('/wms/space/warehouses', payload)
      return data
    },
    async listZones(warehouseId: string): Promise<Zone[]> {
      const { data } = await client.get('/wms/space/zones', { params: { warehouse_id: warehouseId } })
      return data
    },
    async createZone(payload: CreateZoneRequest): Promise<IdResult> {
      const { data } = await client.post('/wms/space/zones', payload)
      return data
    },
    async createArea(payload: CreateAreaRequest): Promise<IdResult> {
      const { data } = await client.post('/wms/space/areas', payload)
      return data
    },
    async createLocation(payload: CreateLocationRequest): Promise<IdResult> {
      const { data } = await client.post('/wms/space/locations', payload)
      return data
    },
    async listLocations(warehouseId: string, zoneId?: string): Promise<Location[]> {
      const { data } = await client.get('/wms/space/locations', {
        params: { warehouse_id: warehouseId, zone_id: zoneId },
      })
      return data
    },
    async patchLocationStatus(locationId: string, payload: ToggleStatusRequest): Promise<IdResult> {
      const { data } = await client.patch(`/wms/space/locations/${locationId}/status`, payload)
      return data
    },
    async getWarehouseTree(warehouseId: string): Promise<SpaceTreeResponse> {
      const { data } = await client.get(`/wms/space/warehouses/${warehouseId}/tree`)
      return data
    },
    async createBin(payload: CreateBinRequest): Promise<IdResult> {
      const { data } = await client.post('/wms/space/bins', payload)
      return data
    },
    async createEquipment(payload: CreateEquipmentRequest): Promise<IdResult> {
      const { data } = await client.post('/wms/space/equipments', payload)
      return data
    },
  },

  positions: {
    async query(params: {
      sku_id?: string
      location_id?: string
      warehouse_id?: string
      inventory_status?: string
    }): Promise<InventoryPosition[]> {
      const { data } = await client.get('/wms/inventory-positions', { params })
      return data
    },
    async queryByLocationCode(warehouseId: string, locationCode: string): Promise<InventoryPosition[]> {
      const { data } = await client.get(`/wms/inventory-positions/by-location/${locationCode}`, {
        params: { warehouse_id: warehouseId },
      })
      return data
    },
    async aggregate(skuId: string, warehouseId: string): Promise<InventoryPositionAggregate[]> {
      const { data } = await client.get('/wms/inventory-positions/aggregate', {
        params: { sku_id: skuId, warehouse_id: warehouseId },
      })
      return data
    },
  },

  tasks: {
    async create(payload: CreateTaskRequest): Promise<TaskResult> {
      const { data } = await client.post('/wms/tasks', payload)
      return data
    },
    async list(params: {
      status?: string
      assignee_id?: string
      offset?: number
      limit?: number
    }): Promise<WmsTask[]> {
      const { data } = await client.get('/wms/tasks', { params })
      return data
    },
    async assign(taskId: string, payload: AssignTaskRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/tasks/${taskId}/assign`, payload)
      return data
    },
    async claim(taskId: string): Promise<IdResult> {
      const { data } = await client.post(`/wms/tasks/${taskId}/claim`)
      return data
    },
    async cancel(taskId: string): Promise<IdResult> {
      const { data } = await client.post(`/wms/tasks/${taskId}/cancel`)
      return data
    },
  },

  receiving: {
    async execute(receivingId: string, payload: ReceivingExecuteRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/receiving/orders/${receivingId}/execute`, payload)
      return data
    },
  },

  putaway: {
    async execute(putawayId: string, payload: PutawayExecuteRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/putaway/tasks/${putawayId}/execute`, payload)
      return data
    },
  },

  picking: {
    async execute(pickingId: string, payload: PickingExecuteRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/picking/tasks/${pickingId}/execute`, payload)
      return data
    },
  },

  transfer: {
    async submit(transferId: string): Promise<IdResult> {
      const { data } = await client.post(`/wms/transfer/orders/${transferId}/submit`)
      return data
    },
    async approve(transferId: string, payload: TransferApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/transfer/orders/${transferId}/approve`, payload)
      return data
    },
    async execute(transferId: string, payload: TransferExecuteRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/transfer/orders/${transferId}/execute`, payload)
      return data
    },
  },

  shipping: {
    async execute(shippingId: string, payload: ShippingExecuteRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/shipping/orders/${shippingId}/execute`, payload)
      return data
    },
    async confirm(shippingId: string): Promise<IdResult> {
      const { data } = await client.post(`/wms/shipping/orders/${shippingId}/confirm`)
      return data
    },
  },

  reconcile: {
    async run(warehouseId: string): Promise<ReconcileDiff[]> {
      const { data } = await client.post('/wms/reconcile/run', null, {
        params: { warehouse_id: warehouseId },
      })
      return data
    },
    async getDiffs(): Promise<ReconcileDiff[]> {
      const { data } = await client.get('/wms/reconcile/diffs')
      return data
    },
    async resolve(diffId: string, payload: ReconcileResolveRequest): Promise<IdResult> {
      const { data } = await client.post(`/wms/reconcile/diffs/${diffId}/resolve`, null, {
        params: { resolution_note: payload.resolution_note ?? '' },
      })
      return data
    },
  },
}

export type {
  Area,
  Bin,
  Equipment,
  InventoryPosition,
  InventoryPositionAggregate,
  Location,
  ReconcileDiff,
  SpaceTreeResponse,
  Warehouse,
  WmsTask,
  Zone,
} from '@/types/wms'