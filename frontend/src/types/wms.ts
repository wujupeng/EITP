export type ZoneFunction = 'receiving' | 'storage' | 'picking' | 'shipping' | 'qc' | 'blocked'
export type LocationType = 'floor' | 'shelf' | 'cold' | 'frozen'
export type CapacityEnforceMode = 'warn' | 'reject'
export type EquipmentType = 'forklift' | 'pda' | 'scanner' | 'conveyor' | 'agv'
export type InventoryStatus = 'available' | 'frozen' | 'inspection' | 'blocked'
export type WmsTaskType = 'receiving' | 'putaway' | 'picking' | 'transfer' | 'shipping'
export type WmsTaskStatus = 'created' | 'assigned' | 'in_progress' | 'completed' | 'cancelled' | 'failed'
export type TaskPriority = 'high' | 'medium' | 'low'
export type PutawayStrategy = 'nearest' | 'empty_first' | 'same_sku' | 'manual'
export type PickingStrategy = 'fifo' | 'fefo' | 'lifo' | 'nearest' | 'batch'
export type SpaceStatus = 'active' | 'disabled'
export type ReconcileDiffType = 'wms_more' | 'inv_more' | 'status_mismatch'
export type ReconcileDiffStatus = 'open' | 'resolved'

export interface Warehouse {
  warehouse_id: string
  warehouse_code: string
  warehouse_name: string
  address: string | null
  hierarchy_node_id: string | null
  status: SpaceStatus
}

export interface Zone {
  zone_id: string
  warehouse_id: string
  zone_code: string
  zone_name: string
  zone_function: ZoneFunction
  status: SpaceStatus
}

export interface Area {
  area_id: string
  zone_id: string
  area_code: string
  area_name: string
  status: SpaceStatus
}

export interface Location {
  location_id: string
  warehouse_id: string
  zone_id: string
  area_id: string | null
  location_code: string
  location_type: LocationType
  capacity_max_qty: number | null
  capacity_max_weight: number | null
  capacity_max_volume: number | null
  capacity_enforce_mode: CapacityEnforceMode
  coordinate_x: number | null
  coordinate_y: number | null
  coordinate_z: number | null
  status: SpaceStatus
}

export interface Bin {
  bin_id: string
  location_id: string
  bin_code: string
  status: SpaceStatus
}

export interface Equipment {
  equipment_id: string
  warehouse_id: string
  equipment_code: string
  equipment_type: EquipmentType
  status: SpaceStatus
}

export interface SpaceTreeNode {
  zone_id: string
  zone_code: string
  zone_name: string
  zone_function: ZoneFunction
  status: SpaceStatus
  areas: Area[]
  locations: Location[]
}

export interface SpaceTreeResponse {
  warehouse_id: string
  warehouse_code: string
  warehouse_name: string
  status: SpaceStatus
  zones: SpaceTreeNode[]
}

export interface InventoryPosition {
  position_id: string
  sku_id: string
  warehouse_id: string
  location_id: string
  bin_id: string | null
  lot_number: string | null
  batch_number: string | null
  serial_number: string | null
  expiry_date: string | null
  quantity: number
  inventory_status: InventoryStatus
  received_at: string | null
  last_updated_at: string | null
}

export interface InventoryPositionAggregate {
  sku_id: string
  warehouse_id: string
  location_id: string
  total_quantity: number
  status_breakdown: Record<InventoryStatus, number>
}

export interface WmsTask {
  task_id: string
  task_type: WmsTaskType
  document_id: string
  document_type: string
  assignee_id: string | null
  status: WmsTaskStatus
  priority: TaskPriority
  inv_transaction_ids: string[]
  created_at: string | null
  assigned_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface ReconcileDiff {
  diff_id: string
  sku_id: string
  warehouse_id: string
  wms_quantity: number
  inv_quantity: number
  diff_quantity: number
  diff_type: ReconcileDiffType
  status: ReconcileDiffStatus
  created_at: string | null
}

export interface CreateWarehouseRequest {
  warehouse_code: string
  warehouse_name: string
  address?: string
  hierarchy_node_id?: string
}

export interface CreateZoneRequest {
  warehouse_id: string
  zone_code: string
  zone_name: string
  zone_function?: ZoneFunction
}

export interface CreateAreaRequest {
  zone_id: string
  area_code: string
  area_name: string
}

export interface CreateLocationRequest {
  warehouse_id: string
  zone_id: string
  area_id?: string
  location_code: string
  location_type?: LocationType
  capacity_max_qty?: number
  capacity_max_weight?: number
  capacity_max_volume?: number
  capacity_enforce_mode?: CapacityEnforceMode
  coordinate_x?: number
  coordinate_y?: number
  coordinate_z?: number
}

export interface CreateBinRequest {
  location_id: string
  bin_code: string
}

export interface CreateEquipmentRequest {
  warehouse_id: string
  equipment_code: string
  equipment_type?: EquipmentType
}

export interface ToggleStatusRequest {
  activate: boolean
}

export interface CreateTaskRequest {
  task_type: WmsTaskType
  document_id: string
  document_type: string
  priority?: TaskPriority
  idempotency_key?: string
  correlation_id?: string
}

export interface AssignTaskRequest {
  assignee_id: string
}

export interface ReceivingExecuteRequest {
  line_id: string
  received_quantity: number
  location_id: string
  lot_number?: string
  batch_number?: string
  serial_numbers?: string[]
  idempotency_key?: string
}

export interface PutawayExecuteRequest {
  target_location_id: string
  putaway_quantity: number
}

export interface PickingExecuteRequest {
  line_id: string
  picked_quantity: number
}

export interface TransferExecuteRequest {
  line_id: string
  transfer_quantity: number
}

export interface TransferApproveRequest {
  opinion?: string
}

export interface ShippingExecuteRequest {
  logistics_no: string
  logistics_company: string
}

export interface ReconcileResolveRequest {
  resolution_note?: string
}

export interface IdResult {
  [key: string]: string
}

export interface TaskResult {
  task_id: string
  status: WmsTaskStatus
}