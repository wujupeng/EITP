export interface GroupProduct {
  group_product_id: string
  group_product_code: string
  group_product_name: string
  base_unit_id: string
  group_category_id: string | null
  group_brand_id: string | null
  spec_template_id: string | null
  status: string
  published_version: number
  description: string | null
}

export interface GroupSku {
  group_sku_id: string
  group_product_id: string
  group_sku_code: string
  group_sku_name: string
  unit_id: string
  specification_instance: Record<string, unknown> | null
  barcode_list: string[] | null
  weight: number | null
  volume: number | null
  status: string
}

export interface GroupCategory {
  group_category_id: string
  group_category_code: string
  group_category_name: string
  parent_category_id: string | null
  level: number
  status: string
  published_version: number
}

export interface GroupBrand {
  group_brand_id: string
  group_brand_code: string
  group_brand_name: string
  status: string
}

export interface GroupUnit {
  group_unit_id: string
  group_unit_code: string
  group_unit_name: string
  is_base_unit: boolean
}

export interface SpecTemplate {
  template_id: string
  template_code: string
  template_name: string
  template_level: string
  tenant_id: string | null
  attribute_definitions: AttributeDefinition[]
  status: string
}

export interface AttributeDefinition {
  attribute_name: string
  attribute_type: string
  is_required: boolean
  enum_values: string[] | null
  min_value: number | null
  max_value: number | null
}

export interface AttributeTemplate {
  template_id: string
  template_code: string
  template_name: string
  template_level: string
  tenant_id: string | null
  attribute_type: string
  is_required: boolean
  enum_values: string[] | null
  min_value: number | null
  max_value: number | null
  status: string
}

export interface EnterpriseProduct {
  enterprise_product_id: string
  tenant_id: string
  group_product_id: string
  enterprise_product_code: string
  enterprise_product_name: string | null
  enterprise_category_id: string | null
  reference_status: string
  published_version: number
}

export interface EnterpriseSku {
  enterprise_sku_id: string
  tenant_id: string
  enterprise_product_id: string
  group_sku_id: string
  enterprise_sku_code: string | null
  enterprise_sku_name: string | null
  enterprise_barcode_list: string[] | null
  status: string
}

export interface ProductReference {
  reference_id: string
  tenant_id: string
  group_product_id: string
  enterprise_product_id: string
  referenced_by: string
  referenced_at: string
  reference_status: string
  released_by: string | null
  released_at: string | null
}

export interface Customization {
  customization_id: string
  tenant_id: string
  enterprise_product_id: string
  enterprise_sku_id: string | null
  sales_price: number | null
  purchase_price: number | null
  inventory_strategy: string | null
  safety_stock: number | null
  cost_model: string | null
  custom_attributes: Record<string, unknown> | null
  version: number
}

export interface GovernanceRequest {
  workflow_id: string
  entity_type: string
  entity_id: string | null
  governance_level: string
  state: string
  current_version: number
  target_version: number
}

export interface MasterDataVersion {
  version_id: string
  tenant_id: string | null
  entity_type: string
  entity_id: string
  version_number: number
  snapshot_before: Record<string, unknown> | null
  snapshot_after: Record<string, unknown>
  change_type: string
  operated_by: string
  reason: string | null
  operated_at: string
}

export interface VersionCompareResult {
  [key: string]: { before: unknown; after: unknown }
}

export interface NegativePolicyConfig {
  tenant_id: string
  policy_mode: string
}

export interface NegativePolicyAudit {
  audit_id: string
  tenant_id: string
  policy_before: string
  policy_after: string
  operated_by: string
  reason: string
  operated_at: string
}

export interface MasterDataQueryResult {
  enterprise_product: Record<string, unknown>
  group_product: Record<string, unknown> | null
  enterprise_skus: Record<string, unknown>[]
  group_skus: Record<string, unknown>[]
  customization: Record<string, unknown> | null
}

export interface BarcodeLocateResult {
  enterprise_sku_id: string
  enterprise_sku_code: string | null
  enterprise_product_id: string
  barcode_source: string
}

export interface MasterDataAudit {
  audit_id: string
  tenant_id: string | null
  action: string
  entity_type: string
  entity_id: string
  version_number: number | null
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  operated_by: string | null
  operated_at: string
  reason: string | null
  ip_address: string | null
}