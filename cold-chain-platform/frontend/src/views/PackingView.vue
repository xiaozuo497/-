<template>
  <AppShell>
    <div class="page-head">
      <h1>三维装箱</h1>
      <p>仓库按“先送后装、后送先装”的原则复核装车顺序，同一客户使用同一颜色，减少翻箱和错卸。</p>
    </div>

    <div class="packing-layout">
      <el-card shadow="never">
        <template #header>
          <div class="card-toolbar">
            <strong>装箱顺序可视化</strong>
            <el-select v-model="selectedVehicleId" style="width: 260px">
              <el-option v-for="route in solution?.routes || []" :key="route.vehicle_id" :label="route.plate_no" :value="route.vehicle_id" />
            </el-select>
          </div>
        </template>
        <div v-if="currentRoute" class="packing-controls">
          <el-button @click="showPrevious" :disabled="visibleCount <= 1">上一步</el-button>
          <el-slider v-model="visibleCount" :min="1" :max="currentRoute.packing.items.length || 1" show-input />
          <el-button @click="showNext" :disabled="visibleCount >= currentRoute.packing.items.length">下一步</el-button>
          <el-button @click="showAll">显示全部</el-button>
        </div>
        <div ref="canvasRef" class="packing-canvas"></div>
        <div class="legend-row">
          <span v-for="stop in currentRoute?.stops || []" :key="stop.order_id" class="legend-pill">
            <i class="legend-dot" :style="{ '--dot-color': stop.color }"></i>
            {{ stop.customer_name }}
          </span>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>装箱参数</template>
        <template v-if="currentRoute">
          <el-alert
            v-if="currentRoute.packing_feasible === false"
            :title="(currentRoute.constraint_violations || []).join('；') || '该路线无法满足装箱或载重约束'"
            type="error"
            :closable="false"
            class="section-card"
          />
          <el-descriptions :column="1" border>
            <el-descriptions-item label="车辆">{{ currentRoute.plate_no }}</el-descriptions-item>
            <el-descriptions-item label="箱数">{{ currentRoute.packing.box_count }} / {{ currentRoute.packing.requested_box_count }}，标称容量 {{ currentRoute.packing.capacity_count }}</el-descriptions-item>
            <el-descriptions-item label="重量">{{ currentRoute.total_weight_kg }} kg</el-descriptions-item>
            <el-descriptions-item label="装载率">{{ (currentRoute.load_rate * 100).toFixed(2) }}%</el-descriptions-item>
            <el-descriptions-item label="卸货顺序">{{ currentRoute.stops.map((s) => s.customer_name).join(' -> ') }}</el-descriptions-item>
            <el-descriptions-item label="装车顺序">{{ currentRoute.packing_order.join(' -> ') }}</el-descriptions-item>
            <el-descriptions-item label="当前显示">{{ visibleCount }} / {{ currentRoute.packing.items.length }} 箱</el-descriptions-item>
            <el-descriptions-item v-if="currentItem" label="当前箱位">
              {{ currentItem.customer_name }} / {{ currentItem.box_code }} / {{ currentItem.row_code }} {{ currentItem.col_code }} {{ currentItem.level_code }}
            </el-descriptions-item>
          </el-descriptions>

          <el-table :data="currentRoute.packing.items.slice(0, 120)" height="360" class="section-card" size="small">
            <el-table-column prop="seq" label="#" width="54" />
            <el-table-column prop="customer_name" label="客户" min-width="120" />
            <el-table-column label="箱型" width="150">
              <template #default="{ row }">{{ row.box_code }} / {{ row.box_type }}</template>
            </el-table-column>
            <el-table-column label="坐标" width="140">
              <template #default="{ row }">{{ row.row_code }} {{ row.col_code }} {{ row.level_code }}</template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else description="暂无装箱方案，请先在运营总览生成配送方案" />
      </el-card>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

import { getCachedSolution, type OptimizationSolution, type PackingItem } from '../api/orders'
import AppShell from '../components/AppShell.vue'

const canvasRef = ref<HTMLDivElement>()
const solution = ref<OptimizationSolution | null>(null)
const selectedVehicleId = ref('')
const currentRoute = computed(() => solution.value?.routes.find((route) => route.vehicle_id === selectedVehicleId.value) || solution.value?.routes[0])
const visibleCount = ref(1)
const currentItem = computed(() => currentRoute.value?.packing.items[Math.max(0, visibleCount.value - 1)])

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let animationId = 0

function makeTextSprite(text: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 96
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = 'rgba(15, 23, 42, 0.88)'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 34px Microsoft YaHei'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, canvas.width / 2, canvas.height / 2)
  const texture = new THREE.CanvasTexture(canvas)
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(1.2, 0.45, 1)
  return sprite
}

function addBox(item: PackingItem) {
  if (!scene) return
  const geometry = new THREE.BoxGeometry(item.length_cm / 40, item.height_cm / 40, item.width_cm / 40)
  const material = new THREE.MeshLambertMaterial({ color: item.customer_color, transparent: true, opacity: 0.88 })
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.set(item.x_cm / 40, item.y_cm / 40, item.z_cm / 40)
  mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: 0x0f172a })))
  scene.add(mesh)
  const label = makeTextSprite(item.box_code)
  label.position.set(item.x_cm / 40, item.y_cm / 40 + item.height_cm / 80 + 0.28, item.z_cm / 40)
  scene.add(label)
}

function render() {
  nextTick(() => {
    const container = canvasRef.value
    if (!container || !currentRoute.value) return
    if (animationId) cancelAnimationFrame(animationId)
    container.innerHTML = ''
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf6f7fb)
    camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 1000)
    camera.position.set(7.5, 5.2, 8)
    camera.lookAt(0, 0, 0)
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)
    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.autoRotate = false
    controls.target.set(0, 0, 0)

    const ambient = new THREE.AmbientLight(0xffffff, 0.65)
    scene.add(ambient)
    const light = new THREE.DirectionalLight(0xffffff, 0.85)
    light.position.set(8, 10, 6)
    scene.add(light)
    scene.add(new THREE.GridHelper(18, 30, 0x8e8e93, 0xd2d2d7))

    const truck = new THREE.Mesh(
      new THREE.BoxGeometry(408 / 40, 210 / 40, 210 / 40),
      new THREE.MeshBasicMaterial({ color: 0x0071e3, wireframe: true }),
    )
    scene.add(truck)

    currentRoute.value.packing.items.slice(0, visibleCount.value).forEach(addBox)
    drawFrame()
  })
}

function drawFrame() {
  if (!renderer || !scene || !camera) return
  controls?.update()
  renderer.render(scene, camera)
  animationId = requestAnimationFrame(drawFrame)
}

function showPrevious() {
  visibleCount.value = Math.max(1, visibleCount.value - 1)
}

function showNext() {
  visibleCount.value = Math.min(currentRoute.value?.packing.items.length || 1, visibleCount.value + 1)
}

function showAll() {
  visibleCount.value = currentRoute.value?.packing.items.length || 1
}

watch(selectedVehicleId, () => {
  visibleCount.value = Math.min(24, currentRoute.value?.packing.items.length || 1)
  render()
})

watch(visibleCount, render)

onMounted(() => {
  solution.value = getCachedSolution()
  selectedVehicleId.value = solution.value?.routes[0]?.vehicle_id || ''
  visibleCount.value = Math.min(24, currentRoute.value?.packing.items.length || 1)
  render()
})
</script>
