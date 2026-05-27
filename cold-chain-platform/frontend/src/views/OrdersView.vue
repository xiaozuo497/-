<template>
  <AppShell>
    <div class="page-head">
      <h1>订单管理</h1>
      <p>导入、校验和复核配送订单。系统会拦截地址待复核、时间窗异常、缺少箱型或箱数异常的订单，避免不可靠数据进入优化。</p>
    </div>

    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-toolbar">
          <div class="toolbar-left">
            <strong>订单列表</strong>
            <el-tag>{{ orders.length }} 单</el-tag>
            <el-tag v-if="riskCount" type="warning">{{ riskCount }} 单需复核</el-tag>
          </div>
          <div class="toolbar-right">
            <el-button @click="downloadTemplate">下载模板</el-button>
            <el-upload :show-file-list="false" accept=".xlsx,.xls,.csv" :before-upload="importSheet">
              <el-button type="primary">导入 Excel/CSV</el-button>
            </el-upload>
            <el-button @click="dialogVisible = true">新增订单</el-button>
            <el-button type="warning" :disabled="!reviewCount" @click="verifyAllReviewed">确认待复核坐标</el-button>
            <el-button @click="refresh">刷新</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="riskCount"
        class="order-risk-alert"
        type="warning"
        :closable="false"
        :title="`发现 ${riskCount} 单基础数据需复核：地址、坐标、箱型、箱数或时间窗会直接影响路径优化结果。`"
      />

      <el-table :data="orders" height="560" empty-text="暂无订单">
        <el-table-column prop="order_no" label="订单号" width="170" />
        <el-table-column prop="destination_name" label="客户/目的地" min-width="150" />
        <el-table-column prop="destination_address" label="地址" min-width="190" />
        <el-table-column label="定位" width="110">
          <template #default="{ row }">
            <el-tag :type="row.geocode_status === 'needs_review' ? 'warning' : 'success'">
              {{ row.geocode_status === 'needs_review' ? '待复核' : '已确认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="box_count" label="箱数" width="80" />
        <el-table-column label="箱型" width="150">
          <template #default="{ row }">
            <el-tag>{{ row.box_type_code || '-' }}</el-tag>
            <span class="muted"> {{ row.box_type_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间窗" width="170">
          <template #default="{ row }">{{ timeOnly(row.ready_time) }} - {{ timeOnly(row.due_time) }}</template>
        </el-table-column>
        <el-table-column prop="contact_name" label="联系人" width="100" />
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="orderStatus(row).type">{{ orderStatus(row).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-if="row.geocode_status === 'needs_review'" text type="primary" @click="verifyOrder(row)">确认坐标</el-button>
            <el-button text type="danger" @click="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增订单" width="560px">
      <el-alert title="保存后系统会自动解析经纬度；如果只能使用兜底坐标，该订单会被标记为待复核。" type="info" :closable="false" />
      <el-form label-position="top" class="section-card">
        <el-form-item label="客户/目的地">
          <el-input v-model="form.destination_name" placeholder="例如：滁州清流路商超" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.destination_address" placeholder="例如：滁州市南谯区清流路商超" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="周转箱型号">
              <el-select v-model="form.box_type_id" class="full-width">
                <el-option v-for="box in boxTypes" :key="box.id" :label="`${box.code} / ${box.name}`" :value="box.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="箱数">
              <el-input-number v-model="form.box_count" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存并定位</el-button>
      </template>
    </el-dialog>
  </AppShell>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import * as XLSX from 'xlsx'

import {
  createOrder,
  deleteOrder,
  getCachedSolution,
  listBoxTypes,
  listOrders,
  updateOrder,
  type BoxType,
  type OptimizationSolution,
  type Order,
} from '../api/orders'
import AppShell from '../components/AppShell.vue'

type SheetRow = Record<string, unknown>

const orders = ref<Order[]>([])
const boxTypes = ref<BoxType[]>([])
const solution = ref<OptimizationSolution | null>(null)
const dialogVisible = ref(false)
const form = reactive({
  destination_name: '',
  destination_address: '',
  box_type_id: '',
  box_count: 12,
})

const riskCount = computed(() => orders.value.filter(orderHasRisk).length)
const reviewCount = computed(() => orders.value.filter((order) => order.geocode_status === 'needs_review').length)
const optimizedStops = computed(() => {
  const map = new Map<string, { tardiness_min: number }>()
  solution.value?.routes.forEach((route) => {
    route.stops.forEach((stop) => map.set(stop.order_id, { tardiness_min: stop.tardiness_min }))
  })
  return map
})

function timeOnly(value?: string) {
  return value ? new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '-'
}

function orderHasRisk(order: Order) {
  const ready = order.ready_time ? new Date(order.ready_time).getTime() : Number.NaN
  const due = order.due_time ? new Date(order.due_time).getTime() : Number.NaN
  return !order.destination_address || !order.lat || !order.lng || order.box_count <= 0 ||
    !order.box_type_id || !Number.isFinite(ready) || !Number.isFinite(due) || ready >= due ||
    order.geocode_status === 'needs_review'
}

function orderStatus(order: Order): { label: string; type: 'success' | 'warning' | 'danger' | 'info' | 'primary' } {
  if (orderHasRisk(order)) return { label: '需复核', type: 'warning' }
  const optimized = optimizedStops.value.get(order.id)
  if (optimized) return optimized.tardiness_min > 0 ? { label: '迟到风险', type: 'danger' } : { label: '已优化', type: 'primary' }
  if (order.status === 'dispatched') return { label: '已派单', type: 'success' }
  if (order.status === 'in_transit') return { label: '在途', type: 'primary' }
  if (order.status === 'delivered') return { label: '已送达', type: 'success' }
  if (order.status === 'exception') return { label: '异常', type: 'danger' }
  return { label: '待调度', type: 'info' }
}

function cell(row: SheetRow, names: string[], fallback = '') {
  for (const name of names) {
    const value = row[name]
    if (value !== undefined && value !== null && String(value).trim() !== '') return String(value).trim()
  }
  return fallback
}

function excelDate(value: string, fallbackHours: number) {
  if (!value) {
    const date = new Date()
    date.setHours(fallbackHours, 0, 0, 0)
    return date.toISOString()
  }
  const date = new Date(value)
  if (!Number.isNaN(date.getTime())) return date.toISOString()
  const match = value.match(/(\d{1,2}):(\d{1,2})/)
  const result = new Date()
  result.setHours(match ? Number(match[1]) : fallbackHours, match ? Number(match[2]) : 0, 0, 0)
  return result.toISOString()
}

async function refresh() {
  orders.value = await listOrders()
}

async function submit() {
  const selected = boxTypes.value.find((box) => box.id === form.box_type_id)
  await createOrder({
    order_no: `SO-${Date.now()}`,
    origin_name: '滁州冷链中心',
    destination_name: form.destination_name || '新增客户',
    destination_address: form.destination_address || form.destination_name,
    box_type_id: form.box_type_id,
    box_count: form.box_count,
    unit_weight_kg: selected?.gross_weight_kg ?? 12.6,
    ready_time: excelDate('', 8),
    due_time: excelDate('', 12),
    status: 'pending',
  })
  dialogVisible.value = false
  ElMessage.success('订单已保存，并开始自动解析经纬度')
  await refresh()
}

async function verifyOrder(order: Order) {
  await updateOrder(order.id, { lng: order.lng, lat: order.lat, geocode_status: 'verified' })
  ElMessage.success('坐标已人工确认')
  await refresh()
}

async function verifyAllReviewed() {
  const targets = orders.value.filter((order) => order.geocode_status === 'needs_review' && order.lng && order.lat)
  await Promise.all(targets.map((order) => updateOrder(order.id, { lng: order.lng, lat: order.lat, geocode_status: 'verified' })))
  ElMessage.success(`已确认 ${targets.length} 个待复核坐标`)
  await refresh()
}

async function remove(id: string) {
  await deleteOrder(id)
  ElMessage.success('订单已删除')
  await refresh()
}

function downloadTemplate() {
  const worksheet = XLSX.utils.json_to_sheet([
    {
      订单号: 'SO-NEW-001',
      收货点: '清流路商超',
      地址: '滁州市南谯区清流路商超',
      箱型代码: 'C',
      箱数: 12,
      单箱重量: 12.6,
      起送时间: '08:30',
      要求送达时间: '10:30',
      联系人: '张三',
      电话: '13800000000',
    },
  ])
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '订单导入模板')
  XLSX.writeFile(workbook, '订单导入模板.xlsx')
}

async function importSheet(file: File) {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true })
  const worksheet = workbook.Sheets[workbook.SheetNames[0]]
  const rows = XLSX.utils.sheet_to_json<SheetRow>(worksheet, { defval: '' })
  let imported = 0
  let skipped = 0

  for (const row of rows) {
    const destination = cell(row, ['收货点', '目的地', '客户', '客户名称', '门店', '配送点'])
    if (!destination) {
      skipped += 1
      continue
    }
    const boxText = cell(row, ['箱型代码', '箱型', '周转箱型号', '周转箱', '箱型型号'], 'C')
    const box = boxTypes.value.find((item) => item.code === boxText || item.name === boxText || `${item.code} / ${item.name}` === boxText) || boxTypes.value[2]
    try {
      await createOrder({
        order_no: cell(row, ['订单号', '订单编号', '单号'], `SO-${Date.now()}-${imported}`),
        origin_name: cell(row, ['发货点', '起点'], '滁州冷链中心'),
        destination_name: destination,
        destination_address: cell(row, ['地址', '收货地址', '目的地地址'], destination),
        box_type_id: box?.id,
        box_count: Number(cell(row, ['箱数', '数量', '周转箱数量'], '1')),
        unit_weight_kg: Number(cell(row, ['单箱重量', '重量', '单箱重量kg'], String(box?.gross_weight_kg ?? 12.6))),
        ready_time: excelDate(cell(row, ['起送时间', '最早送达时间', 'ready_time']), 8),
        due_time: excelDate(cell(row, ['要求送达时间', '最晚送达时间', 'due_time']), 12),
        contact_name: cell(row, ['联系人', '收货人']),
        contact_phone: cell(row, ['电话', '联系电话', '手机号']),
        status: 'pending',
      })
      imported += 1
    } catch {
      skipped += 1
    }
  }
  ElMessage.success(`已导入 ${imported} 单，跳过 ${skipped} 单；兜底坐标会进入待复核`)
  await refresh()
  return false
}

onMounted(async () => {
  boxTypes.value = await listBoxTypes()
  form.box_type_id = boxTypes.value[2]?.id || boxTypes.value[0]?.id || ''
  solution.value = getCachedSolution()
  await refresh()
})
</script>
