<template>
  <AppShell>
    <div class="page-head">
      <h1>运营总览</h1>
      <p>集中查看今日订单、车辆、准时率、成本、碳排和异常风险，支撑调度员完成当日配送闭环。</p>
    </div>

    <div class="metric-grid">
      <el-card v-for="metric in metrics" :key="metric.label" shadow="never">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small class="metric-note">{{ metric.note }}</small>
      </el-card>
    </div>

    <el-row :gutter="16" class="dashboard-control-row">
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="section-card control-panel-card">
          <template #header>
            <div class="card-toolbar compact-toolbar">
              <strong>候选方案</strong>
              <el-tag v-if="solutions.length">{{ solutions.length }} 套</el-tag>
            </div>
          </template>
          <el-button type="primary" class="full-width" :loading="loading" @click="runDashboardOptimization">
            运行优化并生成方案
          </el-button>
          <p class="panel-hint">使用当前全部订单和全部可用车辆生成方案，按综合成本从低到高排序。</p>
          <div v-if="solutions.length" class="plan-list compact-plan-list">
            <button
              v-for="(item, index) in solutions"
              :key="`${item.solution_type}-${index}`"
              :class="['plan-card-button', { active: solutionIndex === index }]"
              type="button"
              @click="selectSolution(index)"
            >
              <strong>{{ index + 1 }}. {{ planTitle(item, index) }}</strong>
              <span>成本 ¥{{ item.total_cost.toFixed(2) }} / 准时率 {{ (item.on_time_rate * 100).toFixed(2) }}%</span>
              <small>{{ item.vehicle_count }} 辆车 / {{ item.total_distance_km.toFixed(1) }} km / 迟到 {{ item.total_tardiness_min }} 分钟</small>
            </button>
          </div>
          <el-empty v-else description="暂无方案" :image-size="70" />
          <div class="plan-summary">
            <div>
              <span>车辆</span>
              <strong>{{ solution?.vehicle_count || 0 }} 辆</strong>
            </div>
            <div>
              <span>迟到</span>
              <strong>{{ lateStops.length }} 点</strong>
            </div>
            <div>
              <span>平均货损</span>
              <strong>{{ solution ? `${(solution.avg_loss_rate * 100).toFixed(2)}%` : '-' }}</strong>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="section-card control-panel-card">
          <template #header>
            <div class="card-toolbar compact-toolbar">
              <div class="toolbar-left">
                <strong>车辆管理</strong>
                <el-tag>{{ vehicles.length }} 辆</el-tag>
                <el-tag type="success">{{ availableVehicleCount }} 辆可用</el-tag>
              </div>
              <el-button type="primary" @click="vehicleDialogVisible = true">新增车辆</el-button>
            </div>
          </template>
          <div class="mini-toolbar">
            <el-upload :show-file-list="false" accept=".xlsx,.xls,.csv" :before-upload="importVehicleSheet">
              <el-button>导入车辆信息</el-button>
            </el-upload>
            <el-button @click="downloadVehicleTemplate">车辆模板</el-button>
            <el-button @click="refreshVehicles">刷新</el-button>
          </div>
          <el-table :data="vehicles" height="300" empty-text="暂无车辆">
            <el-table-column prop="plate_no" label="车牌号" width="120" />
            <el-table-column prop="vehicle_type" label="车型" min-width="180" />
            <el-table-column label="车厢尺寸" width="160">
              <template #default="{ row }">{{ row.length_cm }} × {{ row.width_cm }} × {{ row.height_cm }} cm</template>
            </el-table-column>
            <el-table-column label="载重" width="105">
              <template #default="{ row }">{{ row.max_load_kg }} kg</template>
            </el-table-column>
            <el-table-column label="状态" width="130">
              <template #default="{ row }">
                <el-select
                  v-model="row.status"
                  size="small"
                  class="vehicle-status-select"
                  @change="(status: string) => saveVehicleStatus(row, status)"
                >
                  <el-option label="可用" value="available" />
                  <el-option label="维修中" value="maintenance" />
                  <el-option label="停用" value="disabled" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button text type="danger" @click="removeVehicle(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="section-card control-panel-card">
          <template #header>
            <div class="card-toolbar compact-toolbar">
              <div class="toolbar-left">
                <strong>周转箱管理</strong>
                <el-tag>{{ boxTypes.length }} 种箱型</el-tag>
              </div>
              <el-button type="primary" @click="boxDialogVisible = true">新增周转箱</el-button>
            </div>
          </template>
          <div class="mini-toolbar">
            <el-upload :show-file-list="false" accept=".xlsx,.xls,.csv" :before-upload="importBoxSheet">
              <el-button>导入周转箱尺寸</el-button>
            </el-upload>
            <el-button @click="downloadBoxTemplate">箱型模板</el-button>
            <el-button @click="refreshBoxTypes">刷新</el-button>
          </div>
          <el-table :data="boxTypes" height="300" empty-text="暂无周转箱">
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="name" label="型号" min-width="150" />
            <el-table-column label="外尺寸" width="150">
              <template #default="{ row }">{{ row.length_cm }} × {{ row.width_cm }} × {{ row.height_cm }} cm</template>
            </el-table-column>
            <el-table-column label="数量" width="140">
              <template #default="{ row }">
                <el-input-number
                  :model-value="row.stock_quantity"
                  :min="0"
                  size="small"
                  class="stock-input"
                  @change="(value: number | undefined) => saveBoxStock(row.id, value ?? 0)"
                />
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button text type="danger" @click="removeBoxType(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" class="section-card">
          <template #header>运营风险提示</template>
          <div class="decision-list">
            <div v-for="item in operationNotices" :key="item.title" class="decision-item">
              <strong>{{ item.title }}</strong>
              <p>{{ item.body }}</p>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="section-card">
          <template #header>数据接入与执行</template>
          <div class="action-grid">
            <el-upload :show-file-list="false" accept=".xlsx,.xls,.csv" :before-upload="importOrderSheet">
              <button class="action-tile" type="button">
                <strong>导入订单</strong>
                <span>Excel / CSV</span>
              </button>
            </el-upload>
            <button class="action-tile" type="button" @click="router.push('/optimization')">
              <strong>查看路径地图</strong>
              <span>路线与 QGIS 输出</span>
            </button>
            <button class="action-tile" type="button" :disabled="!solution" @click="router.push('/driver')">
              <strong>司机任务</strong>
              <span>到达时间与异常点</span>
            </button>
            <button class="action-tile" type="button" :disabled="!solution" @click="dispatchCurrentSolution">
              <strong>派单执行</strong>
              <span>写入司机任务状态流</span>
            </button>
            <button class="action-tile" type="button" :disabled="!solution" @click="reportTrafficException">
              <strong>异常重优化</strong>
              <span>记录异常并重新计算</span>
            </button>
            <button class="action-tile" type="button" :disabled="!solution" @click="exportArchive">
              <strong>导出复盘数据</strong>
              <span>CSV 班次归档</span>
            </button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never" class="section-card">
          <template #header>今日工作流</template>
          <el-steps direction="vertical">
            <el-step
              v-for="step in workflowSteps"
              :key="step.title"
              :title="step.title"
              :description="step.description"
              :status="step.status"
            />
          </el-steps>
        </el-card>

        <el-card shadow="never" class="section-card">
          <template #header>复盘归档</template>
          <div class="archive-summary">
            <div v-for="item in archiveItems" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
          <el-alert
            class="section-card"
            :type="solution ? 'success' : 'info'"
            :closable="false"
            :title="archivePrompt"
          />
          <el-form label-position="top" class="section-card">
            <el-form-item label="异常原因">
              <el-select v-model="reviewForm.reason" class="full-width">
                <el-option label="无异常" value="无异常" />
                <el-option label="客户时间窗过紧" value="客户时间窗过紧" />
                <el-option label="车辆不足" value="车辆不足" />
                <el-option label="装车延误" value="装车延误" />
                <el-option label="路况异常" value="路况异常" />
                <el-option label="客户收货延迟" value="客户收货延迟" />
              </el-select>
            </el-form-item>
            <el-form-item label="复盘结论">
              <el-input v-model="reviewForm.note" type="textarea" :rows="3" placeholder="记录本班次成本、迟到、装载和异常处理结果" />
            </el-form-item>
            <el-button type="primary" :disabled="!solution" @click="saveReview">保存复盘</el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="arrivalRows.length" shadow="never" class="section-card">
      <template #header>订单抵达跟踪</template>
      <el-table :data="arrivalRows" height="360">
        <el-table-column prop="order_no" label="订单号" width="150" />
        <el-table-column prop="customer_name" label="客户" min-width="150" />
        <el-table-column prop="plate_no" label="车辆" width="120" />
        <el-table-column prop="estimated_arrival" label="高德路径预计抵达" width="160" />
        <el-table-column prop="due_time" label="要求送达" width="110" />
        <el-table-column label="实际抵达" width="120">
          <template #default="{ row }">{{ row.actual_arrival || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.actual_arrival ? 'success' : row.tardiness_min ? 'danger' : 'info'">
              {{ row.actual_arrival ? '已送达' : row.tardiness_min ? '预计迟到' : '待送达' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header>历史方案对比</template>
          <el-table :data="historyRows" height="260" empty-text="暂无历史方案">
            <el-table-column prop="solution_type" label="方案" min-width="160" />
            <el-table-column label="成本" width="90">
              <template #default="{ row }">¥{{ row.total_cost.toFixed(0) }}</template>
            </el-table-column>
            <el-table-column label="准时率" width="90">
              <template #default="{ row }">{{ (row.on_time_rate * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="车辆" prop="vehicle_count" width="70" />
            <el-table-column label="碳排" width="90">
              <template #default="{ row }">{{ row.total_carbon_kg.toFixed(1) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header>异常事件</template>
          <el-table :data="exceptions" height="260" empty-text="暂无异常">
            <el-table-column prop="exception_type" label="类型" width="120" />
            <el-table-column prop="description" label="说明" min-width="180" />
            <el-table-column prop="status" label="状态" width="120" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="vehicleDialogVisible" title="新增车辆" width="680px">
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="添加数量">
              <el-input-number v-model="vehicleForm.add_count" :min="1" :max="50" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车牌号/编号">
              <el-input v-model="vehicleForm.plate_no" placeholder="例如：皖M-L005；多辆时自动追加 -01" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="车型">
          <el-input v-model="vehicleForm.vehicle_type" placeholder="例如：4.2米冷藏车 / 插电式混合动力冷藏车" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="车厢长(cm)">
              <el-input-number v-model="vehicleForm.length_cm" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="车厢宽(cm)">
              <el-input-number v-model="vehicleForm.width_cm" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="车厢高(cm)">
              <el-input-number v-model="vehicleForm.height_cm" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="有效容积(m³)">
              <el-input-number v-model="vehicleForm.volume_m3" :min="0.01" :precision="2" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大载重(kg)">
              <el-input-number v-model="vehicleForm.max_load_kg" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="温区">
              <el-select v-model="vehicleForm.temperature_zone" class="full-width">
                <el-option label="冷藏" value="冷藏" />
                <el-option label="冷冻" value="冷冻" />
                <el-option label="常温" value="常温" />
                <el-option label="多温区" value="多温区" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="车辆状态">
          <el-select v-model="vehicleForm.status" class="full-width">
            <el-option label="可用" value="available" />
            <el-option label="维修中" value="maintenance" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="vehicleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitVehicles">保存车辆</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="boxDialogVisible" title="新增周转箱" width="640px">
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="箱型代码">
              <el-input v-model="boxForm.code" placeholder="例如：C" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="型号">
              <el-input v-model="boxForm.name" placeholder="例如：LH-600-220" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数量">
              <el-input-number v-model="boxForm.quantity" :min="0" class="full-width" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="长(cm)">
              <el-input-number v-model="boxForm.length_cm" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="宽(cm)">
              <el-input-number v-model="boxForm.width_cm" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="高(cm)">
              <el-input-number v-model="boxForm.height_cm" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="单箱重量(kg)">
              <el-input-number v-model="boxForm.gross_weight_kg" :min="0.01" :precision="2" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="boxForm.enabled" class="full-width">
                <el-option label="启用" :value="true" />
                <el-option label="停用" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="boxDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBoxType">保存周转箱</el-button>
      </template>
    </el-dialog>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'

import {
  createBoxType,
  createDispatch,
  createOperationException,
  createOrder,
  createVehicle,
  deleteBoxType,
  deleteVehicle,
  getLatestSelectedSolution,
  getCachedSolutions,
  compareRecentSolutions,
  importBoxTypes,
  importVehicles,
  listBoxTypes,
  listDeliveryRecords,
  listOperationExceptions,
  listOrders,
  listVehicles,
  runOptimization,
  updateBoxTypeStock,
  updateVehicleStatus,
  type BoxType,
  type OptimizationSolution,
  type OptimizationHistoryRow,
  type OperationException,
  type Order,
  type Vehicle,
} from '../api/orders'
import AppShell from '../components/AppShell.vue'

type StepStatus = 'wait' | 'process' | 'finish' | 'error' | 'success'
type SheetRow = Record<string, unknown>
interface DeliveryState {
  actualArrival: string
  completedAt: string
}

const REVIEW_STORAGE_KEY = 'cold-chain-review'

const router = useRouter()
const orderCount = ref(0)
const vehicleCount = ref(0)
const orders = ref<Order[]>([])
const vehicles = ref<Vehicle[]>([])
const boxTypes = ref<BoxType[]>([])
const vehicleDialogVisible = ref(false)
const boxDialogVisible = ref(false)
const loading = ref(false)
const solutions = ref<OptimizationSolution[]>([])
const solutionIndex = ref(0)
const solution = computed(() => solutions.value[solutionIndex.value] ?? null)
const deliveryRecords = ref<Record<string, DeliveryState>>({})
const historyRows = ref<OptimizationHistoryRow[]>([])
const exceptions = ref<OperationException[]>([])
const reviewForm = reactive(loadReview())
const vehicleForm = reactive({
  add_count: 1,
  plate_no: '',
  vehicle_type: '冷藏车',
  length_cm: 408,
  width_cm: 210,
  height_cm: 210,
  volume_m3: 18.14,
  max_load_kg: 3380,
  temperature_zone: '冷藏',
  status: 'available',
})
const boxForm = reactive({
  code: '',
  name: '',
  quantity: 0,
  length_cm: 60,
  width_cm: 40,
  height_cm: 22,
  gross_weight_kg: 12.6,
  enabled: true,
})

const lateStops = computed(() => solution.value?.routes.flatMap((route) => route.stops.filter((stop) => stop.tardiness_min > 0)) || [])
const usedVehicles = computed(() => solution.value?.vehicle_count || solution.value?.routes.length || 0)
const availableVehicleCount = computed(() => vehicles.value.filter((vehicle) => vehicle.status === 'available').length)
const avgLoadRate = computed(() => {
  const routes = solution.value?.routes || []
  if (!routes.length) return 0
  return routes.reduce((sum, route) => sum + route.load_rate, 0) / routes.length
})
const maxLoadRate = computed(() => Math.max(...(solution.value?.routes.map((route) => route.load_rate) || [0])))
const totalStops = computed(() => solution.value?.routes.reduce((sum, route) => sum + route.stops.length, 0) || 0)
const archiveReady = computed(() => Boolean(solution.value))
const arrivalRows = computed(() => {
  if (!solution.value) return []
  return solution.value.routes.flatMap((route) =>
    route.stops.map((stop) => ({
      ...stop,
      plate_no: route.plate_no,
      estimated_arrival: stop.arrival_time,
      actual_arrival: deliveryRecords.value[stop.order_id]?.actualArrival || '',
    })),
  )
})

async function refreshDeliveryRecords() {
  const records = await listDeliveryRecords()
  deliveryRecords.value = Object.fromEntries(records.map((record) => [
    record.order_id,
    {
      actualArrival: new Date(record.actual_arrival).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }),
      completedAt: record.actual_arrival,
    },
  ]))
}

function loadReview() {
  const raw = localStorage.getItem(REVIEW_STORAGE_KEY)
  if (!raw) return { reason: '无异常', note: '' }
  try {
    return { reason: '无异常', note: '', ...JSON.parse(raw) }
  } catch {
    return { reason: '无异常', note: '' }
  }
}

function saveReview() {
  localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(reviewForm))
  ElMessage.success('复盘已保存')
}

function sortSolutions(items: OptimizationSolution[]) {
  return [...items].sort((a, b) =>
    a.total_cost - b.total_cost ||
    b.on_time_rate - a.on_time_rate ||
    a.total_tardiness_min - b.total_tardiness_min ||
    a.vehicle_count - b.vehicle_count
  )
}

function planTitle(item: OptimizationSolution, index: number) {
  if (index === 0) return `当前成本最低方案 / ${item.vehicle_count}辆车`
  return item.solution_type
    .replace(/最优方案：准时率100%后成本最低/g, '准时优先方案')
    .replace(/综合成本最小方案/g, '载重均衡方案')
    .replace(/综合成本最小/g, '载重均衡')
}

function persistSolutions() {
  localStorage.setItem('cold-chain-all-solutions', JSON.stringify(solutions.value))
  localStorage.setItem('cold-chain-last-solution', JSON.stringify(solution.value ?? null))
}

function selectSolution(index: number) {
  solutionIndex.value = index
  persistSolutions()
}

function stepStatus(done: boolean, active: boolean, failed = false): StepStatus {
  if (failed) return 'error'
  if (done) return 'finish'
  if (active) return 'process'
  return 'wait'
}

const workflowSteps = computed(() => {
  const hasOrders = orderCount.value > 0
  const hasVehicles = availableVehicleCount.value > 0
  const hasSolution = Boolean(solution.value)
  const hasLate = lateStops.value.length > 0
  const packingReady = hasSolution && !hasLate
  const driverReady = hasSolution
  return [
    {
      title: '订单导入',
      description: hasOrders ? `已读取 ${orderCount.value} 单，下一步校验地址、时间窗和箱数。` : '请先导入订单或新增订单。',
      status: stepStatus(hasOrders, !hasOrders),
    },
    {
      title: '路径优化',
      description: hasSolution
        ? `已生成 ${usedVehicles.value} 辆车方案，准时率 ${(solution.value!.on_time_rate * 100).toFixed(2)}%。`
        : hasOrders && hasVehicles ? '订单和车辆已准备，可运行路径优化。' : '等待订单和车辆资料。',
      status: stepStatus(hasSolution, hasOrders && hasVehicles && !hasSolution),
    },
    {
      title: '仓库装车',
      description: packingReady ? '装车顺序可在三维装箱页面复核。' : hasLate ? '存在迟到风险，先调整方案再装车。' : '等待路径方案。',
      status: stepStatus(packingReady, hasSolution && !packingReady, hasLate),
    },
    {
      title: '司机执行',
      description: driverReady ? `已生成 ${totalStops.value} 个配送点的到达时间和异常标记。` : '等待路径方案后派发司机任务。',
      status: stepStatus(driverReady, false),
    },
    {
      title: '复盘归档',
      description: archiveReady.value ? '成本、里程、碳排、迟到点和装载率已可归档。' : '优化完成后自动汇总复盘数据。',
      status: stepStatus(archiveReady.value, false),
    },
  ]
})

const metrics = computed(() => [
  { label: '待调度订单', value: `${orderCount.value} 单`, note: orderCount.value ? '已进入今日调度池' : '等待导入订单' },
  { label: '可用车辆', value: `${availableVehicleCount.value} 辆`, note: solution.value ? `本次使用 ${usedVehicles.value} 辆` : '等待生成方案' },
  { label: '准时送达率', value: solution.value ? `${(solution.value.on_time_rate * 100).toFixed(2)}%` : '待生成', note: lateStops.value.length ? `${lateStops.value.length} 个风险点` : '以客户时间窗为准' },
  { label: '配送成本', value: solution.value ? `¥${solution.value.total_cost.toFixed(2)}` : '待生成', note: solution.value ? `${solution.value.total_distance_km.toFixed(1)} km / ${solution.value.total_carbon_kg.toFixed(1)} kgCO2e` : '生成方案后展示' },
])

const operationNotices = computed(() => {
  if (!solution.value) {
    return [
      { title: '尚未生成配送方案', body: '请先导入订单、维护车辆，再生成配送方案。没有方案时，系统只能展示资源规模，不能判断今日履约风险。' },
      { title: '数据接入待配置', body: '订单、车辆和司机任务可先通过 Excel 台账流转；上线前应完成 TMS、WMS 或 API 对接配置，减少重复录入。' },
    ]
  }
  return [
    {
      title: solution.value.is_feasible ? '今日方案可进入执行' : '今日方案需要调度复核',
      body: solution.value.is_feasible
        ? '当前方案满足所有订单时间窗，可以进入装车和司机派发。'
        : `当前有 ${lateStops.value.length} 个迟到点，总迟到 ${solution.value.total_tardiness_min} 分钟。执行项：追加车辆、拆分批次或调整客户时间窗。`,
    },
    {
      title: '成本口径需可追溯',
      body: `本次配送成本 ¥${solution.value.total_cost.toFixed(2)}，里程 ${solution.value.total_distance_km.toFixed(1)} km。归档表已包含油电费、司机工时、过路费和客户赔付字段。`,
    },
    {
      title: maxLoadRate.value > 0.92 ? '装载弹性不足' : '装载弹性可接受',
      body: `平均装载率 ${(avgLoadRate.value * 100).toFixed(1)}%，最高装载率 ${(maxLoadRate.value * 100).toFixed(1)}%。高装载率会降低临时加单和包装误差的缓冲空间。`,
    },
  ]
})

const archiveItems = computed(() => [
  { label: '归档订单', value: solution.value ? `${totalStops.value} 单` : '-' },
  { label: '使用车辆', value: solution.value ? `${usedVehicles.value} 辆` : '-' },
  { label: '总迟到', value: solution.value ? `${solution.value.total_tardiness_min} 分钟` : '-' },
  { label: '平均装载率', value: solution.value ? `${(avgLoadRate.value * 100).toFixed(1)}%` : '-' },
])

const archivePrompt = computed(() => {
  if (!solution.value) return '完成路径优化后，系统会汇总本班次复盘数据。'
  if (lateStops.value.length) return '归档前记录迟到原因，例如客户时间窗过紧、车辆不足、装车延误或路况异常。'
  return '本班次无迟到风险，可归档为准时执行样本，用于成本和排班对比。'
})

function cell(row: SheetRow, names: string[], fallback = '') {
  for (const name of names) {
    const value = row[name]
    if (value !== undefined && value !== null && String(value).trim() !== '') return String(value).trim()
  }
  return fallback
}

function numberCell(row: SheetRow, names: string[], fallback: number) {
  const value = Number(cell(row, names, String(fallback)))
  return Number.isFinite(value) && value > 0 ? value : fallback
}

function vehicleStatusText(status: string) {
  if (status === 'available') return '可用'
  if (status === 'maintenance') return '维修中'
  if (status === 'disabled') return '停用'
  return status || '-'
}

function vehiclePlate(index: number) {
  const base = vehicleForm.plate_no.trim()
  if (vehicleForm.add_count <= 1) return base
  return `${base}-${String(index + 1).padStart(2, '0')}`
}

async function refreshOrders() {
  orders.value = await listOrders()
  orderCount.value = orders.value.length
}

async function refreshVehicles() {
  vehicles.value = await listVehicles()
  vehicleCount.value = vehicles.value.length
}

async function refreshBoxTypes() {
  boxTypes.value = await listBoxTypes()
}

async function submitVehicles() {
  if (!vehicleForm.plate_no.trim()) {
    ElMessage.warning('请输入车牌号或车辆编号')
    return
  }
  const createdIds: string[] = []
  let failed = 0
  for (let index = 0; index < vehicleForm.add_count; index += 1) {
    try {
      const created = await createVehicle({
        plate_no: vehiclePlate(index),
        vehicle_type: vehicleForm.vehicle_type,
        length_cm: vehicleForm.length_cm,
        width_cm: vehicleForm.width_cm,
        height_cm: vehicleForm.height_cm,
        volume_m3: vehicleForm.volume_m3,
        max_load_kg: vehicleForm.max_load_kg,
        temperature_zone: vehicleForm.temperature_zone,
        status: vehicleForm.status,
      })
      createdIds.push(created.id)
    } catch {
      failed += 1
    }
  }
  await refreshVehicles()
  vehicleDialogVisible.value = false
  ElMessage.success(`已新增 ${createdIds.length} 辆车${failed ? `，${failed} 辆未保存` : ''}`)
}

async function removeVehicle(id: string) {
  await deleteVehicle(id)
  ElMessage.success('车辆已删除')
  await refreshVehicles()
}

async function saveVehicleStatus(row: Vehicle, status: string) {
  try {
    const updated = await updateVehicleStatus(row.id, status)
    const target = vehicles.value.find((vehicle) => vehicle.id === row.id)
    if (target) target.status = updated.status
    ElMessage.success(`车辆状态已更新为${vehicleStatusText(updated.status)}`)
  } catch {
    await refreshVehicles()
    ElMessage.error('车辆状态更新失败')
  }
}

async function submitBoxType() {
  if (!boxForm.code.trim() || !boxForm.name.trim()) {
    ElMessage.warning('请输入箱型代码和型号')
    return
  }
  try {
    await createBoxType({
      code: boxForm.code.trim(),
      name: boxForm.name.trim(),
      length_cm: boxForm.length_cm,
      width_cm: boxForm.width_cm,
      height_cm: boxForm.height_cm,
      gross_weight_kg: boxForm.gross_weight_kg,
      stock_quantity: boxForm.quantity,
      enabled: boxForm.enabled,
    })
    await refreshBoxTypes()
    boxDialogVisible.value = false
    ElMessage.success('周转箱已保存')
  } catch {
    ElMessage.error('周转箱未保存，请检查箱型代码或型号是否重复')
  }
}

async function removeBoxType(id: string) {
  await deleteBoxType(id)
  ElMessage.success('周转箱已删除')
  await refreshBoxTypes()
}

async function saveBoxStock(id: string, quantity: number) {
  const updated = await updateBoxTypeStock(id, Math.max(0, Number(quantity) || 0))
  const target = boxTypes.value.find((box) => box.id === id)
  if (target) target.stock_quantity = updated.stock_quantity
  ElMessage.success('周转箱数量已更新')
}

async function runDashboardOptimization() {
  const orderIds = orders.value.map((order) => order.id)
  const vehicleIds = vehicles.value.filter((vehicle) => vehicle.status === 'available').map((vehicle) => vehicle.id)
  if (!orderIds.length || !vehicleIds.length) {
    ElMessage.warning('请先导入订单并维护可用车辆')
    return
  }
  loading.value = true
  try {
    const result = await runOptimization(orderIds, vehicleIds)
    if (!result.solutions.length) {
      solutions.value = []
      solutionIndex.value = 0
      persistSolutions()
      ElMessage.error('当前订单和车辆无法生成满足载重、容积、箱数等基础约束的方案。')
      return
    }
    solutions.value = sortSolutions(result.solutions)
    solutionIndex.value = 0
    persistSolutions()
    await refreshOrders()
    ElMessage.success('优化完成：已按综合成本从低到高展示方案')
  } catch (error: unknown) {
    const detail = typeof error === 'object' && error && 'response' in error
      ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : undefined
    ElMessage.error(detail || '优化失败，请检查订单、车辆和周转箱库存')
  } finally {
    loading.value = false
  }
}

async function dispatchCurrentSolution() {
  if (!solution.value) return
  const taskId = localStorage.getItem('cold-chain-last-task-id') || undefined
  const rows = await createDispatch(solution.value, taskId)
  ElMessage.success(`已派发 ${rows.length} 个司机任务`)
  await refreshOrders()
}

async function reportTrafficException() {
  const firstStop = solution.value?.routes[0]?.stops[0]
  await createOperationException({
    order_id: firstStop?.order_id,
    vehicle_id: solution.value?.routes[0]?.vehicle_id,
    exception_type: 'traffic',
    description: '调度端记录路况异常，建议重新优化剩余订单。',
    trigger_reoptimization: true,
  })
  exceptions.value = await listOperationExceptions()
  await runDashboardOptimization()
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

async function importOrderSheet(file: File) {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true })
  const worksheet = workbook.Sheets[workbook.SheetNames[0]]
  const rows = XLSX.utils.sheet_to_json<SheetRow>(worksheet, { defval: '' })
  let imported = 0
  let skipped = 0

  for (const row of rows) {
    const destination = cell(row, ['收货地', '目的地', '客户', '客户名称', '门店', '配送点'])
    if (!destination) {
      skipped += 1
      continue
    }
    const boxText = cell(row, ['箱型代码', '箱型', '周转箱型号', '周转箱', '箱型型号'], 'C')
    const box = boxTypes.value.find((item) => item.code === boxText || item.name === boxText || `${item.code} / ${item.name}` === boxText) || boxTypes.value[2]
    try {
      await createOrder({
        order_no: cell(row, ['订单号', '订单编号', '单号'], `SO-${Date.now()}-${imported}`),
        origin_name: cell(row, ['发货地', '起点'], '滁州冷链中心'),
        destination_name: destination,
        destination_address: cell(row, ['地址', '收货地址', '目的地地址'], destination),
        box_type_id: box?.id,
        box_count: Number(cell(row, ['箱数', '数量', '周转箱数量'], '1')),
        unit_weight_kg: Number(cell(row, ['单箱重量', '重量', '单箱重量kg'], String(box?.gross_weight_kg ?? 12.6))),
        ready_time: excelDate(cell(row, ['起送时间', '最早送达时间', 'ready_time']), 8),
        due_time: excelDate(cell(row, ['要求送达时间', '最晚送达时间', 'due_time']), 12),
        contact_name: cell(row, ['联系人', '收货人']),
        contact_phone: cell(row, ['电话', '联系电话', '手机号']),
        status: '待调度',
      })
      imported += 1
    } catch {
      skipped += 1
    }
  }
  await refreshOrders()
  ElMessage.success(`已导入 ${imported} 单，跳过 ${skipped} 单`)
  return false
}

function downloadRows(rows: Record<string, unknown>[], sheetName: string, fileName: string) {
  const worksheet = XLSX.utils.json_to_sheet(rows)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)
  XLSX.writeFile(workbook, fileName)
}

function downloadVehicleTemplate() {
  downloadRows([
    {
      车牌号: '皖M-L005',
      车型: 'BJ5045XLCPHEV2 插电式混合动力冷藏车',
      长cm: 408,
      宽cm: 210,
      高cm: 210,
      容积m3: 18.14,
      载重kg: 3380,
      温区: '冷藏',
      状态: 'available',
    },
  ], '车辆模板', '车辆信息导入模板.xlsx')
}

function downloadBoxTemplate() {
  downloadRows([
    {
      箱型代码: 'C',
      型号: 'LH-600-220',
      长cm: 60,
      宽cm: 40,
      高cm: 22,
      单箱重量kg: 12.6,
      数量: 200,
      启用: '是',
    },
  ], '箱型模板', '周转箱尺寸导入模板.xlsx')
}

async function sheetRows(file: File) {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true })
  const worksheet = workbook.Sheets[workbook.SheetNames[0]]
  return XLSX.utils.sheet_to_json<SheetRow>(worksheet, { defval: '' })
}

async function importVehicleSheet(file: File) {
  const rows = await sheetRows(file)
  const payload: Partial<Vehicle>[] = rows.map((row) => ({
    plate_no: cell(row, ['车牌号', '车牌', 'plate_no']),
    vehicle_type: cell(row, ['车型', '车辆类型', 'vehicle_type'], '冷藏车'),
    length_cm: numberCell(row, ['长cm', '长度cm', 'length_cm'], 408),
    width_cm: numberCell(row, ['宽cm', '宽度cm', 'width_cm'], 210),
    height_cm: numberCell(row, ['高cm', '高度cm', 'height_cm'], 210),
    volume_m3: numberCell(row, ['容积m3', '体积m3', 'volume_m3'], 18.14),
    max_load_kg: numberCell(row, ['载重kg', '最大载重kg', 'max_load_kg'], 3380),
    temperature_zone: cell(row, ['温区', 'temperature_zone'], '冷藏'),
    status: cell(row, ['状态', 'status'], 'available'),
  })).filter((item) => item.plate_no)
  const result = await importVehicles(payload)
  await refreshVehicles()
  ElMessage.success(`车辆资料已导入 ${result.upserted ?? payload.length} 条`)
  return false
}

async function importBoxSheet(file: File) {
  const rows = await sheetRows(file)
  const payload: Partial<BoxType>[] = rows.map((row) => ({
    code: cell(row, ['箱型代码', '代码', 'code']),
    name: cell(row, ['型号', '箱型', '周转箱型号', 'name']),
    length_cm: numberCell(row, ['长cm', '长度cm', 'length_cm'], 60),
    width_cm: numberCell(row, ['宽cm', '宽度cm', 'width_cm'], 40),
    height_cm: numberCell(row, ['高cm', '高度cm', 'height_cm'], 22),
    gross_weight_kg: numberCell(row, ['单箱重量kg', '重量kg', 'gross_weight_kg'], 12.6),
    stock_quantity: numberCell(row, ['数量', '库存数量', '周转箱数量', 'stock_quantity'], 0),
    enabled: !['否', 'false', '0'].includes(cell(row, ['启用', 'enabled'], '是').toLowerCase()),
  })).filter((item) => item.code && item.name)
  const result = await importBoxTypes(payload)
  await refreshBoxTypes()
  ElMessage.success(`周转箱资料已导入 ${result.upserted ?? payload.length} 条`)
  return false
}

function exportArchive() {
  if (!solution.value) return
  const rows = [
    ['指标', '数值'],
    ['归档订单', `${totalStops.value} 单`],
    ['使用车辆', `${usedVehicles.value} 辆`],
    ['总成本', `¥${solution.value.total_cost.toFixed(2)}`],
    ['总里程', `${solution.value.total_distance_km.toFixed(1)} km`],
    ['总碳排', `${solution.value.total_carbon_kg.toFixed(1)} kgCO2e`],
    ['准时率', `${(solution.value.on_time_rate * 100).toFixed(2)}%`],
    ['总迟到', `${solution.value.total_tardiness_min} 分钟`],
    ['平均装载率', `${(avgLoadRate.value * 100).toFixed(1)}%`],
    ['油电费', '待录入'],
    ['司机工时', '待录入'],
    ['过路费', '待录入'],
    ['客户赔付', lateStops.value.length ? '待核算' : '0'],
    ['迟到原因', lateStops.value.length ? '待填写' : '无'],
    ['复盘异常原因', reviewForm.reason],
    ['复盘结论', reviewForm.note || ''],
  ]
  const csv = rows.map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = '班次复盘归档.csv'
  link.click()
  URL.revokeObjectURL(link.href)
}

onMounted(async () => {
  const [orderRows, vehicleRows, boxes] = await Promise.all([listOrders(), listVehicles(), listBoxTypes()])
  orders.value = orderRows
  vehicles.value = vehicleRows
  orderCount.value = orderRows.length
  vehicleCount.value = vehicleRows.length
  boxTypes.value = boxes
  solutions.value = sortSolutions(getCachedSolutions())
  if (!solutions.value.length) {
    const latest = await getLatestSelectedSolution()
    if (latest?.payload) {
      solutions.value = sortSolutions([latest.payload])
      localStorage.setItem('cold-chain-all-solutions', JSON.stringify(solutions.value))
      localStorage.setItem('cold-chain-last-solution', JSON.stringify(solutions.value[0]))
      localStorage.setItem('cold-chain-last-task-id', latest.task_id)
    }
  }
  solutionIndex.value = 0
  persistSolutions()
  await refreshDeliveryRecords()
  historyRows.value = await compareRecentSolutions()
  exceptions.value = await listOperationExceptions()
  window.addEventListener('focus', refreshDeliveryRecords)
})
</script>
