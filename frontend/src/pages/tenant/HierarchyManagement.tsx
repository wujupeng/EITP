import { useState, useEffect } from 'react'
import { Card, Typography, Tree, Button, Modal, Form, Input, InputNumber, Space, Spin, message } from 'antd'
import type { TreeDataNode } from 'antd'
import { client } from '@/api/client'

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
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const fetchTree = async () => {
    setLoading(true)
    try {
      const response = await client.get<HierarchyNode[]>('/tenant/hierarchy/tree')
      setTreeData(buildTreeData(response.data))
    } catch {
      message.error('加载层级树失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTree()
  }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await client.post('/tenant/hierarchy/nodes', values)
      message.success('节点创建成功')
      setModalOpen(false)
      form.resetFields()
      fetchTree()
    } catch {
      message.error('节点创建失败')
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
            <InputNumber min={1} max={7} />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="parent_id" label="父节点 ID">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
