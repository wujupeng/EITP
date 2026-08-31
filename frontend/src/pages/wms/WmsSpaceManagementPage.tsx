import { useState, useEffect } from 'react'
import {
  Card, Table, Button, Modal, Form, Input, Select, InputNumber, Space, Tag, Tree, message, Tabs, Row, Col,
} from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import { wmsApi } from '@/api/wms'
import type { Zone, Location, SpaceTreeResponse } from '@/types/wms'


const ZONE_FUNCTIONS = ['receiving', 'storage', 'picking', 'shipping', 'qc', 'blocked']
const LOCATION_TYPES = ['floor', 'shelf', 'cold', 'frozen']
const EQUIPMENT_TYPES = ['forklift', 'pda', 'scanner', 'conveyor', 'agv']

export default function WmsSpaceManagementPage() {

  const [zones, setZones] = useState<Zone[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [treeData, setTreeData] = useState<DataNode[]>([])
  const [loading, setLoading] = useState(false)
  const [activeWarehouseId, setActiveWarehouseId] = useState<string>('')
  const [modalOpen, setModalOpen] = useState(false)
  const [modalType, setModalType] = useState<'warehouse' | 'zone' | 'area' | 'location' | 'bin' | 'equipment'>('warehouse')
  const [form] = Form.useForm()

  const loadWarehouses = async () => {
    setLoading(true)
    try {
      void await wmsApi.positions.query({})
    } catch {
      // warehouses list endpoint not exposed separately; use tree if available
    } finally {
      setLoading(false)
    }
  }

  const loadZones = async (warehouseId: string) => {
    if (!warehouseId) return
    setLoading(true)
    try {
      const data = await wmsApi.space.listZones(warehouseId)
      setZones(data)
    } catch {
      message.error('加载库区失败')
    } finally {
      setLoading(false)
    }
  }

  const loadLocations = async (warehouseId: string) => {
    if (!warehouseId) return
    setLoading(true)
    try {
      const data = await wmsApi.space.listLocations(warehouseId)
      setLocations(data)
    } catch {
      message.error('加载库位失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTree = async (warehouseId: string) => {
    if (!warehouseId) return
    try {
      const tree: SpaceTreeResponse = await wmsApi.space.getWarehouseTree(warehouseId)
      const nodes: DataNode[] = [
        {
          key: tree.warehouse_id,
          title: `${tree.warehouse_code} - ${tree.warehouse_name} [${tree.status}]`,
          children: tree.zones.map((z) => ({
            key: z.zone_id,
            title: `${z.zone_code} - ${z.zone_name} (${z.zone_function})`,
            children: z.locations.map((l) => ({
              key: l.location_id,
              title: `${l.location_code} [${l.location_type}] ${l.status}`,
            })),
          })),
        },
      ]
      setTreeData(nodes)
    } catch {
      message.error('加载空间树失败')
    }
  }

  useEffect(() => {
    loadWarehouses()
  }, [])

  useEffect(() => {
    if (activeWarehouseId) {
      loadZones(activeWarehouseId)
      loadLocations(activeWarehouseId)
      loadTree(activeWarehouseId)
    }
  }, [activeWarehouseId])

  const openModal = (type: typeof modalType) => {
    setModalType(type)
    form.resetFields()
    setModalOpen(true)
  }

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      switch (modalType) {
        case 'warehouse': {
          const res = await wmsApi.space.createWarehouse({
            warehouse_code: values.warehouse_code,
            warehouse_name: values.warehouse_name,
            address: values.address,
          })
          message.success('仓库创建成功')
          if (res.warehouse_id) setActiveWarehouseId(res.warehouse_id)
          break
        }
        case 'zone': {
          await wmsApi.space.createZone({
            warehouse_id: activeWarehouseId,
            zone_code: values.zone_code,
            zone_name: values.zone_name,
            zone_function: values.zone_function,
          })
          message.success('库区创建成功')
          loadZones(activeWarehouseId)
          break
        }
        case 'area': {
          await wmsApi.space.createArea({
            zone_id: values.zone_id,
            area_code: values.area_code,
            area_name: values.area_name,
          })
          message.success('区域创建成功')
          break
        }
        case 'location': {
          await wmsApi.space.createLocation({
            warehouse_id: activeWarehouseId,
            zone_id: values.zone_id,
            location_code: values.location_code,
            location_type: values.location_type,
            capacity_max_qty: values.capacity_max_qty,
            capacity_max_weight: values.capacity_max_weight,
            capacity_max_volume: values.capacity_max_volume,
            capacity_enforce_mode: values.capacity_enforce_mode,
            coordinate_x: values.coordinate_x,
            coordinate_y: values.coordinate_y,
            coordinate_z: values.coordinate_z,
          })
          message.success('库位创建成功')
          loadLocations(activeWarehouseId)
          break
        }
        case 'bin': {
          await wmsApi.space.createBin({
            location_id: values.location_id,
            bin_code: values.bin_code,
          })
          message.success('料箱创建成功')
          break
        }
        case 'equipment': {
          await wmsApi.space.createEquipment({
            warehouse_id: activeWarehouseId,
            equipment_code: values.equipment_code,
            equipment_type: values.equipment_type,
          })
          message.success('设备创建成功')
          break
        }
      }
      setModalOpen(false)
      if (activeWarehouseId) loadTree(activeWarehouseId)
    } catch {
      message.error('创建失败')
    }
  }

  const handleToggleLocation = async (locationId: string, activate: boolean) => {
    try {
      await wmsApi.space.patchLocationStatus(locationId, { activate })
      message.success(activate ? '已启用' : '已停用')
      loadLocations(activeWarehouseId)
      loadTree(activeWarehouseId)
    } catch {
      message.error('操作失败')
    }
  }

  const zoneColumns = [
    { title: '库区编码', dataIndex: 'zone_code', key: 'zone_code' },
    { title: '库区名称', dataIndex: 'zone_name', key: 'zone_name' },
    { title: '功能', dataIndex: 'zone_function', key: 'zone_function', render: (v: string) => <Tag>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
  ]

  const locationColumns = [
    { title: '库位编码', dataIndex: 'location_code', key: 'location_code' },
    { title: '类型', dataIndex: 'location_type', key: 'location_type', render: (v: string) => <Tag>{v}</Tag> },
    { title: '最大容量', dataIndex: 'capacity_max_qty', key: 'capacity_max_qty' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Location) => (
        <Button
          size="small"
          onClick={() => handleToggleLocation(record.location_id, record.status !== 'active')}
        >
          {record.status === 'active' ? '停用' : '启用'}
        </Button>
      ),
    },
  ]

  const renderModalForm = () => {
    switch (modalType) {
      case 'warehouse':
        return (
          <>
            <Form.Item name="warehouse_code" label="仓库编码" rules={[{ required: true }]}>
              <Input placeholder="如 WH-001" />
            </Form.Item>
            <Form.Item name="warehouse_name" label="仓库名称" rules={[{ required: true }]}>
              <Input placeholder="如 华东中心仓" />
            </Form.Item>
            <Form.Item name="address" label="地址">
              <Input placeholder="仓库地址" />
            </Form.Item>
          </>
        )
      case 'zone':
        return (
          <>
            <Form.Item name="zone_code" label="库区编码" rules={[{ required: true }]}>
              <Input placeholder="如 Z-RECEIVING" />
            </Form.Item>
            <Form.Item name="zone_name" label="库区名称" rules={[{ required: true }]}>
              <Input placeholder="如 收货区" />
            </Form.Item>
            <Form.Item name="zone_function" label="库区功能" initialValue="storage">
              <Select options={ZONE_FUNCTIONS.map((f) => ({ label: f, value: f }))} />
            </Form.Item>
          </>
        )
      case 'area':
        return (
          <>
            <Form.Item name="zone_id" label="所属库区" rules={[{ required: true }]}>
              <Select options={zones.map((z) => ({ label: `${z.zone_code} - ${z.zone_name}`, value: z.zone_id }))} />
            </Form.Item>
            <Form.Item name="area_code" label="区域编码" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="area_name" label="区域名称" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </>
        )
      case 'location':
        return (
          <>
            <Form.Item name="zone_id" label="所属库区" rules={[{ required: true }]}>
              <Select options={zones.map((z) => ({ label: `${z.zone_code} - ${z.zone_name}`, value: z.zone_id }))} />
            </Form.Item>
            <Form.Item name="location_code" label="库位编码" rules={[{ required: true }]}>
              <Input placeholder="如 A-01-01-01" />
            </Form.Item>
            <Form.Item name="location_type" label="库位类型" initialValue="shelf">
              <Select options={LOCATION_TYPES.map((t) => ({ label: t, value: t }))} />
            </Form.Item>
            <Form.Item name="capacity_max_qty" label="最大容量（件）">
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item name="capacity_max_weight" label="最大承重（kg）">
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item name="capacity_max_volume" label="最大体积（m³）">
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item name="capacity_enforce_mode" label="超容策略" initialValue="reject">
              <Select options={[{ label: '拒绝', value: 'reject' }, { label: '警告', value: 'warn' }]} />
            </Form.Item>
            <Row gutter={8}>
              <Col span={8}><Form.Item name="coordinate_x" label="X"><InputNumber /></Form.Item></Col>
              <Col span={8}><Form.Item name="coordinate_y" label="Y"><InputNumber /></Form.Item></Col>
              <Col span={8}><Form.Item name="coordinate_z" label="Z"><InputNumber /></Form.Item></Col>
            </Row>
          </>
        )
      case 'bin':
        return (
          <>
            <Form.Item name="location_id" label="所属库位" rules={[{ required: true }]}>
              <Select options={locations.map((l) => ({ label: l.location_code, value: l.location_id }))} />
            </Form.Item>
            <Form.Item name="bin_code" label="料箱编码" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </>
        )
      case 'equipment':
        return (
          <>
            <Form.Item name="equipment_code" label="设备编码" rules={[{ required: true }]}>
              <Input placeholder="如 EQ-001" />
            </Form.Item>
            <Form.Item name="equipment_type" label="设备类型" initialValue="forklift">
              <Select options={EQUIPMENT_TYPES.map((t) => ({ label: t, value: t }))} />
            </Form.Item>
          </>
        )
    }
  }

  const modalTitle = {
    warehouse: '创建仓库', zone: '创建库区', area: '创建区域',
    location: '创建库位', bin: '创建料箱', equipment: '创建设备',
  }[modalType]

  return (
    <Card>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入仓库 ID 加载空间数据"
          enterButton="加载"
          style={{ width: 400 }}
          onSearch={(val) => setActiveWarehouseId(val.trim())}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal('warehouse')}>创建仓库</Button>
        {activeWarehouseId && (
          <>
            <Button icon={<PlusOutlined />} onClick={() => openModal('zone')}>创建库区</Button>
            <Button icon={<PlusOutlined />} onClick={() => openModal('location')}>创建库位</Button>
            <Button icon={<PlusOutlined />} onClick={() => openModal('area')}>创建区域</Button>
            <Button icon={<PlusOutlined />} onClick={() => openModal('bin')}>创建料箱</Button>
            <Button icon={<PlusOutlined />} onClick={() => openModal('equipment')}>创建设备</Button>
            <Button icon={<ReloadOutlined />} onClick={() => {
              loadZones(activeWarehouseId); loadLocations(activeWarehouseId); loadTree(activeWarehouseId)
            }}>刷新</Button>
          </>
        )}
      </Space>

      <Tabs
        items={[
          {
            key: 'tree',
            label: '空间树',
            children: treeData.length > 0 ? <Tree treeData={treeData} defaultExpandAll /> : <Tag>请先加载仓库</Tag>,
          },
          {
            key: 'zones',
            label: '库区列表',
            children: <Table columns={zoneColumns} dataSource={zones} rowKey="zone_id" loading={loading} pagination={{ pageSize: 20 }} />,
          },
          {
            key: 'locations',
            label: '库位列表',
            children: <Table columns={locationColumns} dataSource={locations} rowKey="location_id" loading={loading} pagination={{ pageSize: 20 }} />,
          },
        ]}
      />

      <Modal title={modalTitle} open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">{renderModalForm()}</Form>
      </Modal>
    </Card>
  )
}
