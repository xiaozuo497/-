import { getCurrentUser } from './auth'

export type UserRole = 'admin' | 'dispatcher' | 'warehouse' | 'driver'

export interface NavItem {
  path: string
  label: string
  roles: UserRole[]
}

export const ROLE_HOME: Record<UserRole, string> = {
  admin: '/dashboard',
  dispatcher: '/dashboard',
  warehouse: '/packing',
  driver: '/driver',
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: '运营总览', roles: ['admin', 'dispatcher'] },
  { path: '/orders', label: '订单管理', roles: ['admin', 'dispatcher'] },
  { path: '/optimization', label: '路径优化与地图', roles: ['admin', 'dispatcher'] },
  { path: '/packing', label: '三维装箱', roles: ['admin', 'warehouse'] },
  { path: '/driver', label: '司机任务', roles: ['admin', 'dispatcher', 'driver'] },
  { path: '/system', label: '系统诊断与备份', roles: ['admin'] },
]

export function currentRole(): UserRole | null {
  const role = getCurrentUser()?.role
  if (role === 'admin' || role === 'dispatcher' || role === 'warehouse' || role === 'driver') return role
  return null
}

export function homeForCurrentUser() {
  const role = currentRole()
  return role ? ROLE_HOME[role] : '/login'
}

export function canAccessRoute(path: string) {
  const role = currentRole()
  if (!role) return false
  const navItem = NAV_ITEMS.find((item) => item.path === path)
  return navItem ? navItem.roles.includes(role) : true
}

export function visibleNavItems() {
  const role = currentRole()
  if (!role) return []
  return NAV_ITEMS.filter((item) => item.roles.includes(role))
}
