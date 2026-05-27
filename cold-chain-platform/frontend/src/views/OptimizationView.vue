<template>
  <AppShell>
    <div class="page-head">
      <h1>路径优化与地图</h1>
      <p>时间窗先作为强约束；若无法 100% 准时，系统明确给出迟到缺口、风险订单和调度执行项。</p>
    </div>

    <el-row :gutter="16">
      <el-col :span="24">
        <div class="metric-grid">
          <el-card shadow="never">
            <span>综合成本</span>
            <strong class="metric-value"><span>{{ solution ? `¥${solution.total_cost.toFixed(2)}` : '-' }}</span></strong>
          </el-card>
          <el-card shadow="never">
            <span>总里程</span>
            <strong class="metric-value">
              <span>{{ solution?.total_distance_km.toFixed(2) || '-' }}</span>
              <small>km</small>
            </strong>
          </el-card>
          <el-card shadow="never">
            <span>总碳排放</span>
            <strong class="metric-value">
              <span>{{ solution?.total_carbon_kg.toFixed(2) || '-' }}</span>
              <small>kgCO2e</small>
            </strong>
          </el-card>
          <el-card shadow="never">
            <span>准时送达率</span>
            <strong class="metric-value"><span>{{ solution ? `${(solution.on_time_rate * 100).toFixed(2)}%` : '-' }}</span></strong>
          </el-card>
        </div>

        <el-alert
          v-if="solution"
          :title="decisionTitle"
          :description="decisionDescription"
          :type="solution.is_feasible ? 'success' : 'warning'"
          :closable="false"
          show-icon
          class="section-card"
        />

        <el-card v-if="solution" shadow="never" class="section-card">
          <template #header>调度处置</template>
          <div class="decision-list">
            <div v-for="item in managementAdvice" :key="item.title" class="decision-item">
              <strong>{{ item.title }}</strong>
              <p>{{ item.body }}</p>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="section-card route-map-card">
          <template #header>
            <div class="card-toolbar">
              <div class="route-map-title">公路路网地图与 QGIS 输出</div>
              <el-button :disabled="!solution" @click="exportQgis">导出 QGIS 点位文件</el-button>
            </div>
          </template>
          <el-alert v-if="mapStatus" :title="mapStatus" type="warning" :closable="false" class="map-alert" />
          <div ref="mapRef" class="map-board amap-board">
            <div v-if="!solution" class="map-empty">在运营总览生成方案后，这里展示车辆路线</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="solution" shadow="never" class="section-card">
      <template #header>车辆路线明细</template>
      <el-row :gutter="12">
        <el-col v-for="route in solution.routes" :key="route.vehicle_id" :span="8">
          <el-card shadow="never" class="route-card" :style="{ '--route-color': route.color }">
            <strong>{{ route.plate_no }}</strong>
            <p class="muted">{{ route.stops.map((s) => s.customer_name).join(' -> ') }}</p>
            <p>里程 {{ route.distance_km }} km / 成本 ¥{{ route.cost }} / 箱数 {{ route.box_count }}</p>
            <el-alert
              v-if="route.packing_feasible === false"
              :title="(route.constraint_violations || []).join('；') || '该路线无法满足装箱或载重约束'"
              type="error"
              :closable="false"
              class="route-warning"
            />
            <el-table :data="route.stops" size="small">
              <el-table-column prop="sequence" label="#" width="46" />
              <el-table-column prop="customer_name" label="客户" />
              <el-table-column prop="arrival_time" label="到达" width="70" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.tardiness_min ? 'danger' : 'success'">
                    {{ row.tardiness_min ? `迟到${row.tardiness_min}分钟` : '准时' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </AppShell>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import * as XLSX from 'xlsx'

import {
  getMapConfig,
  getCachedSolutions,
  createBoxType,
  createVehicle,
  deleteBoxType,
  deleteVehicle,
  importBoxTypes,
  importVehicles,
  listBoxTypes,
  listOrders,
  listVehicles,
  runOptimization,
  updateBoxTypeStock,
  type BoxType,
  type OptimizationSolution,
  type Order,
  type Vehicle,
} from '../api/orders'
import AppShell from '../components/AppShell.vue'

declare global {
  interface Window {
    AMap?: any
    _AMapSecurityConfig?: { securityJsCode?: string }
  }
}

type SheetRow = Record<string, unknown>

const orders = ref<Order[]>([])
const vehicles = ref<Vehicle[]>([])
const boxTypes = ref<BoxType[]>([])
const vehicleDialogVisible = ref(false)
const boxDialogVisible = ref(false)
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
const selectedOrderIds = ref<string[]>([])
const selectedVehicleIds = ref<string[]>([])
const loading = ref(false)
const solutions = ref<OptimizationSolution[]>([])
const solutionIndex = ref(0)
const solution = computed(() => solutions.value[solutionIndex.value])
const availableVehicleCount = computed(() => vehicles.value.filter((vehicle) => vehicle.status === 'available').length)
const lateStops = computed(() => solution.value?.routes.flatMap((route) => route.stops.filter((stop) => stop.tardiness_min > 0)) || [])
const delaySummary = computed(() => {
  if (!lateStops.value.length) return ''
  const total = lateStops.value.reduce((sum, stop) => sum + stop.tardiness_min, 0)
  const max = Math.max(...lateStops.value.map((stop) => stop.tardiness_min))
  return `预计迟到 ${lateStops.value.length} 单，总迟到约 ${total} 分钟，单点最多约 ${max} 分钟。`
})
const decisionTitle = computed(() => {
  if (!solution.value) return ''
  if (solution.value.is_feasible) return '当前方案同时满足准时、载重和三维装箱约束'
  if (solution.value.packing_feasible === false) return `当前方案有 ${solution.value.infeasible_route_count || 0} 条路线无法满足装箱或载重约束`
  return `未找到 100% 准时方案，${delaySummary.value}`
})
const decisionDescription = computed(() => {
  if (!solution.value) return ''
  if (solution.value.is_feasible) return '可以进入仓库装车与司机派发；系统已保留候选方案，用于临时加单或车辆故障时切换。'
  if (solution.value.packing_feasible === false) {
    return `${(solution.value.constraint_violations || []).slice(0, 2).join('；')}。请更换更大车型、增加车辆或拆分线路后再派发。`
  }
  return '请优先追加车辆、调整发车批次或与客户协商时间窗，避免把风险方案直接派发到一线执行。'
})
const managementAdvice = computed(() => {
  if (!solution.value) return []
  const routeCount = solution.value.routes.length
  const maxLoadRate = Math.max(...solution.value.routes.map((route) => route.load_rate), 0)
  return [
    {
      title: solution.value.is_feasible ? '可以进入执行' : '不要直接派发全部任务',
      body: solution.value.is_feasible
        ? `本方案使用 ${routeCount} 辆车，准时率 100%，适合作为今日执行方案。`
        : `${lateStops.value.length} 个点存在迟到，需要在派单前完成资源或时间窗调整。`,
    },
    {
      title: '财务口径透明',
      body: `综合成本 ¥${solution.value.total_cost.toFixed(2)}，总里程 ${solution.value.total_distance_km.toFixed(1)} km，成本口径不含客户罚金和退货损失。`,
    },
    {
      title: maxLoadRate > 0.92 ? '装载率偏高，执行弹性不足' : '车辆装载弹性可接受',
      body: `最高车辆装载率 ${(maxLoadRate * 100).toFixed(1)}%。高装载率会提高临时加单、包装差异和装卸延误的风险。`,
    },
  ]
})
const mapRef = ref<HTMLDivElement>()
const mapStatus = ref('')
let amap: any = null
let amapLoading: Promise<void> | null = null
let driving: any = null
let mapOverlays: any[] = []

function sortSolutions(items: OptimizationSolution[]) {
  return [...items].sort((a, b) =>
    Number(!a.is_feasible) - Number(!b.is_feasible) ||
    Number(a.packing_feasible === false) - Number(b.packing_feasible === false) ||
    (a.infeasible_route_count || 0) - (b.infeasible_route_count || 0) ||
    a.total_cost - b.total_cost ||
    b.on_time_rate - a.on_time_rate ||
    a.total_tardiness_min - b.total_tardiness_min ||
    a.vehicle_count - b.vehicle_count
  )
}

function persistSolutions() {
  localStorage.setItem('cold-chain-all-solutions', JSON.stringify(solutions.value))
  localStorage.setItem('cold-chain-last-solution', JSON.stringify(solution.value ?? null))
}

function selectSolution(index: number) {
  solutionIndex.value = index
  persistSolutions()
}

function routeNumber(routeIndex: number, stopSequence: number) {
  return solution.value && solution.value.routes.length > 1 ? `${routeIndex + 1}-${stopSequence}` : String(stopSequence)
}

function mapDot(color = '#4f7de8', label = '') {
  return `
    <div class="amap-route-dot" style="--dot-color:${color}" aria-label="${label}">
      <span></span>
    </div>
  `
}

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

async function refreshVehicles() {
  vehicles.value = await listVehicles()
  const availableIds = vehicles.value.filter((vehicle) => vehicle.status === 'available').map((vehicle) => vehicle.id)
  selectedVehicleIds.value = selectedVehicleIds.value.filter((id) => availableIds.includes(id))
  if (!selectedVehicleIds.value.length) {
    selectedVehicleIds.value = availableIds.slice(0, 3)
  }
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
  selectedVehicleIds.value = [...new Set([...selectedVehicleIds.value, ...createdIds])]
  vehicleDialogVisible.value = false
  ElMessage.success(`已新增 ${createdIds.length} 辆车${failed ? `，${failed} 辆未保存` : ''}`)
}

async function removeVehicle(id: string) {
  await deleteVehicle(id)
  selectedVehicleIds.value = selectedVehicleIds.value.filter((item) => item !== id)
  ElMessage.success('车辆已删除')
  await refreshVehicles()
}

async function submitBoxType() {
  if (!boxForm.code.trim() || !boxForm.name.trim()) {
    ElMessage.warning('请输入箱型代码和型号')
    return
  }
  try {
    const created = await createBoxType({
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

async function run() {
  if (!selectedOrderIds.value.length || !selectedVehicleIds.value.length) {
    ElMessage.warning('请至少选择一个订单和一辆车')
    return
  }
  loading.value = true
  try {
    const result = await runOptimization(selectedOrderIds.value, selectedVehicleIds.value)
    if (!result.solutions.length) {
      solutions.value = []
      solutionIndex.value = 0
      clearMap()
      ElMessage.error('当前订单和车辆无法生成满足载重、容积、箱数等基础约束的方案。')
      return
    }
    solutions.value = sortSolutions(result.solutions)
    solutionIndex.value = 0
    persistSolutions()
    orders.value = await listOrders()
    if (solutions.value[0]?.is_feasible) {
      ElMessage.success('优化完成：已按综合成本从低到高展示候选方案')
    } else {
      ElMessage.warning('未找到 100% 准时方案，已生成准时率最高方案并标记迟到线路')
    }
    await renderAmap()
  } catch (error: unknown) {
    const detail = typeof error === 'object' && error && 'response' in error
      ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : undefined
    ElMessage.error(detail || '优化失败，请检查订单、车辆和周转箱库存')
  } finally {
    loading.value = false
  }
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
      内尺寸: '565x365x210mm',
      折叠尺寸: '600x400x55mm',
      说明: '主力周转箱，适合多层装载',
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

async function loadAmap() {
  if (window.AMap) return
  if (amapLoading) return amapLoading
  amapLoading = getMapConfig().then((config) => new Promise<void>((resolve, reject) => {
    if (!config.amap_key) {
      reject(new Error('未配置高德地图 Key'))
      return
    }
    if (config.amap_security_code) {
      window._AMapSecurityConfig = { securityJsCode: config.amap_security_code }
    }
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(config.amap_key)}&plugin=AMap.Driving`
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('高德地图脚本加载失败'))
    document.head.appendChild(script)
  }))
  return amapLoading
}

async function ensureMap() {
  await nextTick()
  if (!mapRef.value) return null
  if (!amap) {
    await loadAmap()
    amap = new window.AMap.Map(mapRef.value, {
      viewMode: '2D',
      zoom: 11,
      center: [118.3168, 32.3036],
      mapStyle: 'amap://styles/normal',
    })
    driving = new window.AMap.Driving({ policy: window.AMap.DrivingPolicy.LEAST_TIME })
  }
  return amap
}

function clearMap() {
  if (!amap) return
  if (mapOverlays.length) {
    amap.remove(mapOverlays)
    mapOverlays = []
    return
  }
  try {
    amap.clearMap()
  } catch {
    // AMap can throw while overlays are still initializing; overlay tracking handles normal cleanup.
  }
}

function drivingSearch(start: [number, number], end: [number, number]) {
  return new Promise<[number, number][]>((resolve) => {
    if (!window.AMap || !driving) {
      resolve([start, end])
      return
    }
    driving.search(new window.AMap.LngLat(start[0], start[1]), new window.AMap.LngLat(end[0], end[1]), (status: string, result: any) => {
      const route = result?.routes?.[0]
      if (status !== 'complete' || !route) {
        resolve([start, end])
        return
      }
      const points: [number, number][] = []
      route.steps?.forEach((step: any) => {
        step.path?.forEach((point: any) => points.push([point.lng, point.lat]))
      })
      resolve(points.length ? points : [start, end])
    })
  })
}

async function renderAmap() {
  if (!solution.value) return
  try {
    mapStatus.value = ''
    const map = await ensureMap()
    if (!map || !window.AMap) return
    clearMap()
    const depot: [number, number] = [118.3168, 32.3036]
    const depotMarker = new window.AMap.Marker({
      position: depot,
      title: '滁州冷链中心',
      content: mapDot('#4f7de8', '配送中心'),
      offset: new window.AMap.Pixel(-11, -11),
      map,
    })
    mapOverlays.push(depotMarker)
    for (const [routeIndex, route] of solution.value.routes.entries()) {
      const path = [depot, ...route.stops.map((stop) => [stop.lng, stop.lat] as [number, number]), depot]
      for (const [index, start] of path.slice(0, -1).entries()) {
        const roadPath = await drivingSearch(start, path[index + 1])
        const targetStop = index < route.stops.length ? route.stops[index] : null
        const isReturn = index >= route.stops.length
        const segmentColor = route.color
        const polyline = new window.AMap.Polyline({
          path: roadPath,
          strokeColor: segmentColor,
          strokeWeight: 7,
          strokeOpacity: isReturn ? 0.78 : 0.92,
          strokeStyle: isReturn ? 'dashed' : 'solid',
          strokeDasharray: isReturn ? [14, 10] : undefined,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: isReturn ? 45 : 55,
          map,
        })
        mapOverlays.push(polyline)
      }
      for (const stop of route.stops) {
        const position: [number, number] = [stop.lng, stop.lat]
        const markerColor = stop.tardiness_min ? '#e5484d' : (stop.color || route.color)
        const marker = new window.AMap.Marker({
          position,
          title: `${routeNumber(routeIndex, stop.sequence)} ${stop.customer_name}${stop.tardiness_min ? `，预计迟到${stop.tardiness_min}分钟` : ''}`,
          content: mapDot(markerColor, stop.customer_name),
          offset: new window.AMap.Pixel(-11, -11),
          zIndex: stop.tardiness_min ? 110 : 100,
          map,
        })
        mapOverlays.push(marker)
      }
    }
    if (mapOverlays.length) {
      map.setFitView(mapOverlays, false, [40, 40, 40, 40])
    }
  } catch (error) {
    mapStatus.value = error instanceof Error ? error.message : '高德地图加载失败'
  }
}

function exportQgis() {
  if (!solution.value) return
  const features: any[] = []
  features.push({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [118.3168, 32.3036] },
    properties: { name: '滁州冷链中心', type: 'depot' },
  })
  for (const route of solution.value.routes) {
    const coordinates = [[118.3168, 32.3036], ...route.stops.map((stop) => [stop.lng, stop.lat]), [118.3168, 32.3036]]
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates },
      properties: { vehicle: route.plate_no, cost: route.cost, distance_km: route.distance_km },
    })
    for (const stop of route.stops) {
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [stop.lng, stop.lat] },
        properties: {
          order_no: stop.order_no,
          customer: stop.customer_name,
          vehicle: route.plate_no,
          arrival_time: stop.arrival_time,
          due_time: stop.due_time,
          status: stop.status,
          tardiness_min: stop.tardiness_min,
        },
      })
    }
  }
  const blob = new Blob([JSON.stringify({ type: 'FeatureCollection', features }, null, 2)], { type: 'application/geo+json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = '路径点位_QGIS.geojson'
  link.click()
  URL.revokeObjectURL(link.href)
}

onMounted(async () => {
  const [orderRows, vehicleRows, boxRows] = await Promise.all([listOrders(), listVehicles(), listBoxTypes()])
  orders.value = orderRows
  vehicles.value = vehicleRows
  boxTypes.value = boxRows
  selectedOrderIds.value = orderRows.map((order) => order.id)
  selectedVehicleIds.value = vehicleRows.filter((vehicle) => vehicle.status === 'available').slice(0, 3).map((vehicle) => vehicle.id)
  solutions.value = sortSolutions(getCachedSolutions())
  solutionIndex.value = 0
  persistSolutions()
  await renderAmap()
})

watch(solutionIndex, async () => {
  persistSolutions()
  await renderAmap()
})
</script>
