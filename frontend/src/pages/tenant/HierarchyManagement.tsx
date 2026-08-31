import { useState, useEffect } from 'react'
import { Card, Typography, Tree, Button, Modal, Form, Input, Select, Space, Spin, message } from 'antd'
import type { TreeDataNode } from 'antd'
import { client } from '@/api/client'
import { useAuthStore } from '@/store/auth'

const { Title, Paragraph } = Typography

interface HierarchyNode {
  id: string
  tenant_id: string
  level: number
  name: string
  parent_id: string | null
  is_active: boolean
  children?: HierarchyNode[]
}

const LEVEL_NAMES: Record<number, string> = {
  1: 'Platform',
  2: 'Tenant',
  3: 'Enterprise',
  4: 'Organization',
  5: 'Site',
  6: 'Warehouse',
  7: 'Location',
}

function buildTreeData(nodes: HierarchyNode[]): TreeDataNode[] {
  const nodeMap = new Map<string, HierarchyNode & { children: HierarchyNode[] }>()
  const roots: (HierarchyNode & { children: HierarchyNode[] })[] = []

  for (const node of nodes) {
    nodeMap.set(node.id, { ...node, children: [] })
  }

  for (const node of nodes) {
    const current = nodeMap.get(node.id)!
    if (node.parent_id && nodeMap.has(node.parent_id)) {
      nodeMap.get(node.parent_id)!.children.push(current)
    } else {
      roots.push(current)
    }
  }

  const toTreeData = (nodes: (HierarchyNode & { children: HierarchyNode[] })[]): TreeDataNode[] =>
    nodes.map((node) => ({
      key: node.id,
      title: (
        <Space>
          <span>{node.name}</span>
          <span style={{ color: '#999', fontSize: '12px' }}>{LEVEL_NAMES[node.level]}</span>
          {!node.is_active && <span style={{ color: '#ff4d4f', fontSize: '12px' }}>(已停用)</span>}
        </Space>
      ),
      children: node.children.length > 0 ? toTreeData(node.children as (HierarchyNode & { children: HierarchyNode[] })[]) : undefined,
    }))

  return toTreeData(roots)
}

export default function HierarchyManagement() {
  const [treeData, setTreeData] = useState<TreeDataNode[]>([])
  const [flatNodes, setFlatNodes] = useState<HierarchyNode[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const watchLevel = Form.useWatch('level', form)
  const tenantToken = useAuthStore((s) => s.tenantToken)

  const fetchTree = async () => {
    setLoading(true)
    try {
      const response = await client.get<HierarchyNode[]>('/tenant/hierarchy/tree')
      setFlatNodes(response.data)
      setTreeData(buildTreeData(response.data))
    } catch {
      message.error('加载层级树失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTree()
  }, [tenantToken])

  const handleCreate = async () => {
    const values = await form.validateFields()
    const payload = {
      level: values.level,
      name: values.name,
      parent_id: values.parent_id || null,
    }
    try {
      await client.post('/tenant/hierarchy/nodes', payload)
      message.success('节点创建成功')
      setModalOpen(false)
      form.resetFields()
      fetchTree()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (Array.isArray(detail)) {
        message.error(`验证失败: ${detail.map((d: any) => d.msg).join(', ')}`)
      } else {
        message.error('节点创建失败')
      }
    }
  }

  return (
    <Card>
      <Title level={3}>租户管理 - 层级管理</Title>
      <Paragraph>
        管理本租户的七层组织层级：Platform → Tenant → Enterprise → Organization → Site → Warehouse → Location
      </Paragraph>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setModalOpen(true)}>创建节点</Button>
        <Button onClick={fetchTree}>刷新</Button>
      </Space>
      <Spin spinning={loading}>
        <Tree
          treeData={treeData}
          showLine
          defaultExpandAll
        />
      </Spin>
      <Modal
        title="创建层级节点"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="level" label="层级" rules={[{ required: true }]}>
            <Select
              placeholder="请选择层级"
              options={Object.entries(LEVEL_NAMES).map(([k, v]) => ({
                value: Number(k),
                label: `${k} - ${v}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="parent_id"
            label="父节点"
            rules={[
              {
                required: watchLevel !== undefined && watchLevel > 1,
                message: `${LEVEL_NAMES[watchLevel] || ''} 层级节点必须有父级（${LEVEL_NAMES[(watchLevel || 2) - 1] || ''} 层级）`,
              },
            ]}
          >
            <Select
              allowClear
              placeholder={
                watchLevel === 1
                  ? 'Platform 为根节点，无需父节点'
                  : watchLevel !== undefined
                    ? `请选择 ${LEVEL_NAMES[watchLevel - 1]} 层级的父节点`
                    : '请先选择层级'
              }
              disabled={watchLevel === undefined || watchLevel === 1}
              options={flatNodes
                .filter((n) => n.level === (watchLevel ?? 0) - 1)
                .map((n) => ({
                  value: n.id,
                  label: `${n.name} [${LEVEL_NAMES[n.level]}]`,
                }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
