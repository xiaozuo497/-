import { apiClient } from './client'

export interface BoxType {
  id: string
  code: string
  name: string
  length_cm: number
  width_cm: number
  height_cm: number
  gross_weight_kg: number
  stock_quantity: number
  enabled: boolean
}

export interface Vehicle {
  id: string
  plate_no: string
  vehicle_type: string
  length_cm: number
  width_cm: number
  height_cm: number
  volume_m3: number
  max_load_kg: number
  temperature_zone: string
  status: string
}

export interface MapConfig {
  amap_key: string
  amap_security_code?: string
}

export interface Order {
  id: string
  order_no: string
  origin_name: string
  destination_name: string
  destination_address?: string
  lng?: number
  lat?: number
  geocode_source?: string
  geocode_status: string
  box_type_id?: string
  box_type_code?: string
  box_type_name?: string
  box_count: number
  unit_weight_kg: number
  ready_time?: string
  due_time?: string
  contact_name?: string
  contact_phone?: string
  status: string
}

export interface PackingItem {
  seq: number
  customer_id: string
  customer_name: string
  customer_color: string
  box_type: string
  box_code: string
  row_code: string
  col_code: string
  level_code: string
  x_cm: number
  y_cm: number
  z_cm: number
  length_cm: number
  width_cm: number
  height_cm: number
  orientation: string
}

export interface RouteStop {
  order_id: string
  order_no: string
  customer_name: string
  address: string
  lat: number
  lng: number
  box_count: number
  unit_weight_kg: number
  box_type: string
  box_code: string
  ready_time: string
  due_time: string
  sequence: number
  arrival_time: string
  tardiness_min: number
  status: string
  segment_distance_km: number
  late_segment: boolean
  color: string
}

export interface RoutePlan {
  vehicle_id: string
  plate_no: string
  vehicle_type: string
  color: string
  stops: RouteStop[]
  packing_order: string[]
  distance_km: number
  cost: number
  carbon_kg: number
  box_count: number
  total_weight_kg: number
  load_rate: number
  on_time_rate: number
  total_tardiness_min: number
  packing_feasible: boolean
  constraint_violations: string[]
  packing: {
    capacity_count: number
    box_count: number
    rows: number
    cols: number
    levels: number
    items: PackingItem[]
    requested_box_count?: number
    overflow_count?: number
    is_feasible?: boolean
    violations?: string[]
  }
}

export interface OptimizationSolution {
  solution_type: string
  is_feasible: boolean
  routes: RoutePlan[]
  total_cost: number
  total_distance_km: number
  total_carbon_kg: number
  avg_loss_rate: number
  on_time_rate: number
  total_tardiness_min: number
  vehicle_count: number
  is_capacity_feasible?: boolean
  packing_feasible: boolean
  infeasible_route_count: number
  constraint_violations: string[]
}

export interface DeliveryRecord {
  id: string
  order_id: string
  vehicle_id?: string
  actual_arrival: string
  status: string
  note?: string
}

export interface DispatchAssignment {
  id: string
  optimization_task_id?: string
  order_id: string
  vehicle_id: string
  route_sequence: number
  planned_arrival?: string
  status: string
}

export interface OperationException {
  id: string
  order_id?: string
  vehicle_id?: string
  exception_type: string
  description?: string
  status: string
  resolution?: string
}

export interface OptimizationHistoryRow {
  task_id: string
  solution_no: number
  solution_type: string
  total_cost: number
  total_distance_km: number
  total_carbon_kg: number
  on_time_rate: number
  vehicle_count: number
  is_selected: boolean
}

export interface LatestSolution {
  task_id: string
  solution_no: number
  solution_type: string
  created_at: string
  payload: OptimizationSolution
}

export interface BackupFile {
  name: string
  path: string
  size: number
  modified_at: string
}

export interface Diagnostics {
  api: string
  environment: string
  database: string
  docker_hint: string
  hostname: string
  backup_dir: string
  document_renderer: string
  order_count?: number
  vehicle_count?: number
  available_vehicle_count?: number
  pending_order_count?: number
  exception_order_count?: number
  backup_count: number
  latest_backup?: BackupFile | null
}

export interface OptimizationResponse {
  status: string
  task: {
    id: string
    task_no: string
    name: string
    status: string
    objective: string
  }
  solutions: OptimizationSolution[]
}

export async function listOrders() {
  const { data } = await apiClient.get<Order[]>('/orders')
  return data
}

export async function createOrder(payload: Partial<Order>) {
  const { data } = await apiClient.post<Order>('/orders', payload)
  return data
}

export async function updateOrder(id: string, payload: Partial<Order>) {
  const { data } = await apiClient.patch<Order>(`/orders/${id}`, payload)
  return data
}

export async function deleteOrder(id: string) {
  await apiClient.delete(`/orders/${id}`)
}

export async function listBoxTypes() {
  const { data } = await apiClient.get<BoxType[]>('/box-types')
  return data
}

export async function createBoxType(payload: Partial<BoxType>) {
  const { data } = await apiClient.post<BoxType>('/box-types', payload)
  return data
}

export async function deleteBoxType(id: string) {
  await apiClient.delete(`/box-types/${id}`)
}

export async function updateBoxTypeStock(id: string, stockQuantity: number) {
  const { data } = await apiClient.patch<BoxType>(`/box-types/${id}/stock`, { stock_quantity: stockQuantity })
  return data
}

export async function listVehicles() {
  const { data } = await apiClient.get<Vehicle[]>('/vehicles')
  return data
}

export async function createVehicle(payload: Partial<Vehicle>) {
  const { data } = await apiClient.post<Vehicle>('/vehicles', payload)
  return data
}

export async function deleteVehicle(id: string) {
  await apiClient.delete(`/vehicles/${id}`)
}

export async function updateVehicleStatus(id: string, status: string) {
  const { data } = await apiClient.patch<Vehicle>(`/vehicles/${id}/status`, { status })
  return data
}

export async function importVehicles(payload: Partial<Vehicle>[]) {
  const { data } = await apiClient.post('/vehicles/import', payload)
  return data
}

export async function importBoxTypes(payload: Partial<BoxType>[]) {
  const { data } = await apiClient.post('/box-types/import', payload)
  return data
}

export async function getMapConfig() {
  const { data } = await apiClient.get<MapConfig>('/map-config')
  return data
}

export async function runOptimization(orderIds: string[], vehicleIds: string[]) {
  const { data } = await apiClient.post<OptimizationResponse>('/optimization/run', {
    name: '今日生鲜配送优化',
    objective: 'on_time_min_cost',
    order_ids: orderIds,
    vehicle_ids: vehicleIds,
  })
  localStorage.setItem('cold-chain-last-solution', JSON.stringify(data.solutions[0] ?? null))
  localStorage.setItem('cold-chain-all-solutions', JSON.stringify(data.solutions))
  localStorage.setItem('cold-chain-last-task-id', data.task.id)
  return data
}

export async function listDeliveryRecords() {
  const { data } = await apiClient.get<DeliveryRecord[]>('/orders/deliveries')
  return data
}

export async function completeDelivery(payload: { order_id: string; vehicle_id?: string; actual_arrival?: string; note?: string }) {
  const { data } = await apiClient.post<DeliveryRecord>('/orders/deliveries/complete', payload)
  return data
}

export async function createDispatch(solution: OptimizationSolution, taskId?: string) {
  const { data } = await apiClient.post<DispatchAssignment[]>('/orders/dispatch', { task_id: taskId, solution })
  return data
}

export async function listDispatchAssignments() {
  const { data } = await apiClient.get<DispatchAssignment[]>('/orders/dispatch')
  return data
}

export async function updateDispatchStatus(id: string, status: string) {
  const { data } = await apiClient.patch<DispatchAssignment>(`/orders/dispatch/${id}`, { status })
  return data
}

export async function createOperationException(payload: {
  order_id?: string
  vehicle_id?: string
  exception_type: string
  description?: string
  trigger_reoptimization?: boolean
}) {
  const { data } = await apiClient.post<OperationException>('/orders/exceptions', payload)
  return data
}

export async function listOperationExceptions() {
  const { data } = await apiClient.get<OperationException[]>('/orders/exceptions')
  return data
}

export async function compareRecentSolutions() {
  const { data } = await apiClient.get<OptimizationHistoryRow[]>('/optimization/history/compare')
  return data
}

export async function getLatestSelectedSolution() {
  const { data } = await apiClient.get<LatestSolution | null>('/optimization/solutions/latest')
  return data
}

export async function getDiagnostics() {
  const { data } = await apiClient.get<Diagnostics>('/diagnostics')
  return data
}

export async function listBackups() {
  const { data } = await apiClient.get<BackupFile[]>('/backups')
  return data
}

export async function createBackup() {
  const { data } = await apiClient.post<BackupFile>('/backups')
  return data
}

export function getCachedSolution(): OptimizationSolution | null {
  const raw = localStorage.getItem('cold-chain-last-solution')
  return raw ? JSON.parse(raw) : null
}

export function getCachedSolutions(): OptimizationSolution[] {
  const raw = localStorage.getItem('cold-chain-all-solutions')
  return raw ? JSON.parse(raw) : []
}
