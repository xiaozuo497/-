import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import { isAuthenticated } from '../api/auth'
import { canAccessRoute, homeForCurrentUser } from '../api/permissions'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: () => homeForCurrentUser() },
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/dashboard', component: () => import('../views/DashboardView.vue') },
    { path: '/orders', component: () => import('../views/OrdersView.vue') },
    { path: '/optimization', component: () => import('../views/OptimizationView.vue') },
    { path: '/packing', component: () => import('../views/PackingView.vue') },
    { path: '/driver', component: () => import('../views/DriverMobileView.vue') },
    { path: '/system', component: () => import('../views/SystemView.vue') },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) {
    return true
  }
  if (!isAuthenticated()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return canAccessRoute(to.path) ? true : homeForCurrentUser()
})

export default router
