<template>
  <div class="driver-page">
    <div class="driver-shell">
      <div class="phone-header">
        <button class="driver-text-button" type="button" @click="handleHeaderBack">{{ headerBackText }}</button>
        <div>
          <strong>司机执行台</strong>
          <span>{{ route?.plate_no || '等待派单' }}</span>
        </div>
        <button class="driver-primary-icon" type="button" :disabled="!route" @click="renderDriverMap">路线图</button>
      </div>

      <template v-if="solution?.routes.length">
        <div v-if="routeOptions.length > 1" class="driver-vehicle-picker">
          <el-select v-model="selectedVehicleId" class="full-width" placeholder="请选择车辆">
            <el-option
              v-for="item in routeOptions"
              :key="item.vehicle_id"
              :label="`${item.plate_no} / ${item.stops.length} 点`"
              :value="item.vehicle_id"
            />
          </el-select>
        </div>

        <section v-if="route" class="driver-hero" :style="{ '--route-color': route.color }">
          <div class="driver-hero-main">
            <span class="driver-status-pill">{{ route.stops.length ? '执行中' : '待发车' }}</span>
            <h1>{{ nextStop?.customer_name || route.plate_no }}</h1>
            <p>{{ nextStop ? `${nextStop.arrival_time} 到达 / ${nextStop.box_count} 箱` : `${route.plate_no} 今日任务` }}</p>
          </div>
          <div class="driver-summary-grid">
            <div>
              <span>站点</span>
              <strong>{{ route.stops.length }}</strong>
            </div>
            <div>
              <span>里程</span>
              <strong>{{ route.distance_km }}</strong>
            </div>
            <div>
              <span>箱数</span>
              <strong>{{ route.box_count }}</strong>
            </div>
          </div>
          <div class="driver-actions">
            <button class="driver-action-button primary" type="button" @click="renderDriverMap">生成路线图</button>
            <button class="driver-action-button" type="button" @click="feedbackVisible = true">反馈问题</button>
          </div>
        </section>

        <section v-if="route" class="driver-map-panel">
          <div class="driver-panel-head">
            <strong>车内路线图</strong>
            <span>按优化顺序生成</span>
          </div>
          <el-alert v-if="mapStatus" :title="mapStatus" type="warning" :closable="false" class="map-alert" />
          <div ref="mapRef" class="driver-map">
            <div class="driver-map-empty">正在生成路线图</div>
          </div>
        </section>

        <section v-if="route" class="driver-panel">
          <div class="driver-panel-head">
            <strong>优化路线与卸货顺序</strong>
            <span>{{ completedCount }} / {{ route.stops.length }} 已完成</span>
          </div>
          <div class="driver-route-list">
            <button
              v-for="stop in route.stops"
              :key="stop.order_id"
              type="button"
              :class="['driver-route-stop', { active: activeStop === stop.order_id }]"
              @click="activeStop = stop.order_id"
            >
              <span class="driver-sequence">{{ stop.sequence }}</span>
              <div>
                <strong>{{ stop.customer_name }}</strong>
                <small>{{ stop.arrival_time }} / {{ stop.box_count }} 箱 / {{ unloadHint(stop.order_id) }}</small>
              </div>
              <el-tag size="small" :type="deliveryRecords[stop.order_id] ? 'success' : stop.tardiness_min ? 'danger' : 'info'">
                {{ deliveryRecords[stop.order_id] ? '已送达' : stop.tardiness_min ? '风险' : '待送达' }}
              </el-tag>
            </button>
          </div>
        </section>

        <section v-if="route" class="driver-panel">
          <div class="driver-panel-head">
            <strong>站点明细</strong>
            <span>按实际卸货顺序执行</span>
          </div>
          <article
            v-for="stop in route.stops"
            :key="stop.order_id"
            class="driver-stop-card"
          >
            <div class="driver-stop-top">
              <div>
                <strong>{{ stop.customer_name }}</strong>
                <span>{{ stop.address }}</span>
              </div>
              <el-tag :type="stop.tardiness_min ? 'danger' : 'success'">
                {{ stop.tardiness_min ? `迟到${stop.tardiness_min}分钟` : '准时' }}
              </el-tag>
            </div>
            <div class="driver-stop-meta">
              <span>预计 {{ stop.arrival_time }}</span>
              <span>要求 {{ stop.due_time }}</span>
              <span>{{ stop.box_code }} {{ stop.box_type }}</span>
            </div>
            <p v-if="deliveryRecords[stop.order_id]" class="driver-delivered">实际抵达 {{ deliveryRecords[stop.order_id].actualArrival }}</p>
            <p class="driver-unload-hint">卸货提示：{{ unloadHint(stop.order_id) }}</p>
            <div class="driver-stop-actions">
              <button class="driver-action-button primary" type="button" @click="activeStop = stop.order_id">查看卸货</button>
              <button class="driver-action-button" type="button" @click="focusStop(stop)">定位</button>
              <button class="driver-action-button warn" type="button" @click="openFeedback(stop.order_id)">反馈</button>
            </div>
          </article>
        </section>
      </template>
      <el-empty v-else description="暂无司机任务，请先在运营总览生成方案" />

      <el-dialog v-model="dialogVisible" title="配送任务" width="360px">
        <template v-if="selectedStop">
          <p><strong>{{ selectedStop.customer_name }}</strong></p>
          <p>{{ selectedStop.address }}</p>
          <p>订单：{{ selectedStop.order_no }}</p>
          <p>箱数：{{ selectedStop.box_count }} / 箱型：{{ selectedStop.box_code }} {{ selectedStop.box_type }}</p>
          <p>预计抵达：{{ selectedStop.arrival_time }} / 要求：{{ selectedStop.due_time }}</p>
          <p>卸货顺序：第 {{ selectedStop.sequence }} 站，优先卸该客户颜色标识箱。</p>
          <div v-if="selectedPackingItems.length" class="unload-box-list">
            <strong>需卸箱位</strong>
            <span v-for="item in selectedPackingItems.slice(0, 12)" :key="item.seq">
              {{ item.box_code }} {{ item.row_code }} {{ item.col_code }} {{ item.level_code }}
            </span>
            <small v-if="selectedPackingItems.length > 12">还有 {{ selectedPackingItems.length - 12 }} 箱，请按同客户颜色继续卸货。</small>
          </div>
          <p v-if="selectedDelivery">实际抵达：{{ selectedDelivery.actualArrival }}</p>
        </template>
        <template #footer>
          <el-button @click="dialogVisible = false">返回上一页</el-button>
          <el-button type="success" :disabled="Boolean(selectedDelivery)" @click="complete">
            {{ selectedDelivery ? '已送达' : '确认送达' }}
          </el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="feedbackVisible" title="反馈给管理员/调度" width="360px">
        <el-form label-position="top">
          <el-form-item label="问题类型">
            <el-select v-model="feedbackForm.exception_type" class="full-width">
              <el-option label="路线不合理" value="route_issue" />
              <el-option label="交通拥堵" value="traffic" />
              <el-option label="卸货困难" value="unloading" />
              <el-option label="装箱/找货问题" value="packing" />
              <el-option label="客户收货异常" value="customer" />
              <el-option label="车辆异常" value="vehicle" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联站点">
            <el-select v-model="feedbackForm.order_id" clearable class="full-width" placeholder="可不选">
              <el-option
                v-for="stop in route?.stops || []"
                :key="stop.order_id"
                :label="`${stop.sequence}. ${stop.customer_name}`"
                :value="stop.order_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="现场说明">
            <el-input
              v-model="feedbackForm.description"
              type="textarea"
              :rows="4"
              placeholder="例如：实际道路限高、卸货口排队、箱位与卸货顺序不一致、时间窗过紧等"
            />
          </el-form-item>
          <el-checkbox v-model="feedbackForm.trigger_reoptimization">建议管理员重新优化剩余路线</el-checkbox>
        </el-form>
        <template #footer>
          <el-button @click="feedbackVisible = false">取消</el-button>
          <el-button type="primary" :loading="feedbackLoading" @click="submitFeedback">提交反馈</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  completeDelivery,
  createOperationException,
  getLatestSelectedSolution,
  getMapConfig,
  listDeliveryRecords,
  type OptimizationSolution,
  type RouteStop,
} from '../api/orders'
import { getCurrentUser, logout } from '../api/auth'

interface DeliveryState {
  actualArrival: string
  completedAt: string
}

const router = useRouter()
const solution = ref<OptimizationSolution | null>(null)
const user = getCurrentUser()
const routeOptions = computed(() => {
  const routes = solution.value?.routes || []
  return user?.role === 'driver' ? routes.slice(0, 1) : routes
})
const selectedVehicleId = ref(routeOptions.value[0]?.vehicle_id || '')
const route = computed(() => routeOptions.value.find((item) => item.vehicle_id === selectedVehicleId.value) || routeOptions.value[0])
const activeStop = ref('')
const dialogVisible = ref(false)
const feedbackVisible = ref(false)
const feedbackLoading = ref(false)
const mapRef = ref<HTMLDivElement>()
const mapStatus = ref('')
const deliveryRecords = ref<Record<string, DeliveryState>>({})
const selectedStop = computed(() => route.value?.stops.find((stop) => stop.order_id === activeStop.value))
const selectedDelivery = computed(() => selectedStop.value ? deliveryRecords.value[selectedStop.value.order_id] : null)
const completedCount = computed(() => route.value?.stops.filter((stop) => deliveryRecords.value[stop.order_id]).length || 0)
const nextStop = computed(() => route.value?.stops.find((stop) => !deliveryRecords.value[stop.order_id]) || route.value?.stops[0])
const headerBackText = computed(() => (user?.role === 'driver' ? '登录页' : '返回后台'))
const selectedPackingItems = computed(() => {
  if (!selectedStop.value || !route.value) return []
  return route.value.packing.items.filter((item) => item.customer_id === selectedStop.value?.order_id)
})
const feedbackForm = reactive({
  order_id: '',
  exception_type: 'route_issue',
  description: '',
  trigger_reoptimization: true,
})
let amap: any = null
let mapMarkers: any[] = []

function timeNow() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

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

function goBack() {
  if (user?.role === 'driver') {
    router.push('/driver')
  } else if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/optimization')
  }
}

function switchAccount() {
  logout()
  router.replace('/login')
}

function handleHeaderBack() {
  if (user?.role === 'driver') {
    switchAccount()
  } else {
    goBack()
  }
}

async function loadLatestSolution() {
  const latest = await getLatestSelectedSolution()
  solution.value = latest?.payload || null
  selectedVehicleId.value = routeOptions.value[0]?.vehicle_id || ''
  await nextTick()
  await renderDriverMap()
}

async function ensureAmap() {
  if ((window as any).AMap) return (window as any).AMap
  const config = await getMapConfig()
  if (!config.amap_key) throw new Error('未配置高德地图 Key，已保留路线顺序和站点坐标')
  if (config.amap_security_code) {
    ;(window as any)._AMapSecurityConfig = { securityJsCode: config.amap_security_code }
  }
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(config.amap_key)}`
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('高德地图脚本加载失败，已保留路线顺序'))
    document.head.appendChild(script)
  })
  return (window as any).AMap
}

async function renderDriverMap() {
  if (!route.value?.stops.length || !mapRef.value) return
  try {
    mapStatus.value = ''
    const AMap = await ensureAmap()
    const depot: [number, number] = [118.3168, 32.3036]
    const path: [number, number][] = [depot, ...route.value.stops.map((stop) => [stop.lng, stop.lat] as [number, number]), depot]
    if (!amap) {
      amap = new AMap.Map(mapRef.value, {
        viewMode: '2D',
        zoom: 11,
        center: depot,
        mapStyle: 'amap://styles/normal',
      })
    }
    if (mapMarkers.length) {
      amap.remove(mapMarkers)
      mapMarkers = []
    }
    const polyline = new AMap.Polyline({
      path,
      strokeColor: route.value.color || '#0f172a',
      strokeWeight: 6,
      strokeOpacity: 0.88,
      lineJoin: 'round',
      lineCap: 'round',
      map: amap,
    })
    mapMarkers.push(polyline)
    const depotMarker = new AMap.Marker({ position: depot, title: '滁州冷链中心', label: { content: '仓', direction: 'top' }, map: amap })
    mapMarkers.push(depotMarker)
    for (const stop of route.value.stops) {
      const marker = new AMap.Marker({
        position: [stop.lng, stop.lat],
        title: `${stop.sequence}. ${stop.customer_name}`,
        label: { content: String(stop.sequence), direction: 'top' },
        map: amap,
      })
      mapMarkers.push(marker)
    }
    amap.setFitView(mapMarkers, false, [32, 32, 32, 32])
  } catch (error) {
    mapStatus.value = error instanceof Error ? error.message : '路线图生成失败'
  }
}

function focusStop(stop: RouteStop) {
  activeStop.value = stop.order_id
  if (amap) {
    amap.setZoomAndCenter(14, [stop.lng, stop.lat])
  }
}

function unloadHint(orderId: string) {
  const items = route.value?.packing.items.filter((item) => item.customer_id === orderId) || []
  if (!items.length) return '按该客户颜色标识卸货'
  const first = items[0]
  const last = items[items.length - 1]
  return `${items.length} 箱，箱位 ${first.row_code}${first.col_code}${first.level_code} 至 ${last.row_code}${last.col_code}${last.level_code}`
}

function openFeedback(orderId = '') {
  feedbackForm.order_id = orderId
  feedbackVisible.value = true
}

async function submitFeedback() {
  if (!feedbackForm.description.trim()) {
    ElMessage.warning('请填写现场说明')
    return
  }
  feedbackLoading.value = true
  try {
    await createOperationException({
      order_id: feedbackForm.order_id || undefined,
      vehicle_id: route.value?.vehicle_id,
      exception_type: feedbackForm.exception_type,
      description: feedbackForm.description.trim(),
      trigger_reoptimization: feedbackForm.trigger_reoptimization,
    })
    ElMessage.success('已反馈给管理员和调度端')
    feedbackVisible.value = false
    feedbackForm.description = ''
    feedbackForm.order_id = ''
  } finally {
    feedbackLoading.value = false
  }
}

async function complete() {
  if (!selectedStop.value || selectedDelivery.value) return
  const actualArrival = new Date().toISOString()
  await completeDelivery({
    order_id: selectedStop.value.order_id,
    vehicle_id: route.value?.vehicle_id,
    actual_arrival: actualArrival,
  })
  deliveryRecords.value = {
    ...deliveryRecords.value,
    [selectedStop.value.order_id]: {
      actualArrival: timeNow(),
      completedAt: actualArrival,
    },
  }
  ElMessage.success('已记录送达状态')
  dialogVisible.value = false
}

watch(selectedVehicleId, () => {
  activeStop.value = ''
  dialogVisible.value = false
  nextTick(renderDriverMap)
})

watch(activeStop, (value) => {
  dialogVisible.value = Boolean(value)
})

watch(dialogVisible, (value) => {
  if (!value) activeStop.value = ''
})

onMounted(async () => {
  await Promise.all([refreshDeliveryRecords(), loadLatestSolution()])
})
</script>
