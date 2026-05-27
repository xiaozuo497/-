<template>
  <el-container class="app-shell">
    <el-aside width="252px" class="app-sidebar">
      <div class="brand">
        <div class="brand-mark">鲜</div>
        <div>
          <strong>生鲜冷链协同</strong>
          <span>物流调度优化平台</span>
        </div>
      </div>
      <el-menu
        router
        :default-active="$route.path"
        background-color="transparent"
        text-color="#475569"
        active-text-color="#111827"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div>
          <strong>桌面运行版</strong>
          <span>本地数据库与服务运行中</span>
        </div>
        <div class="header-actions">
          <el-tag type="success" effect="plain">运行中</el-tag>
          <el-dropdown>
            <button class="user-chip">
              <span>{{ user?.real_name || user?.username }}</span>
              <small>{{ roleText }}</small>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goHome">返回首页</el-dropdown-item>
                <el-dropdown-item @click="goLogin">切换账号</el-dropdown-item>
                <el-dropdown-item divided @click="signOut">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { getCurrentUser, logout } from '../api/auth'
import { homeForCurrentUser, visibleNavItems } from '../api/permissions'

const router = useRouter()
const user = computed(() => getCurrentUser())

const menuItems = computed(() => visibleNavItems())

const roleText = computed(() => {
  const role = user.value?.role
  if (role === 'admin') return '管理员'
  if (role === 'driver') return '司机'
  if (role === 'warehouse') return '仓库员'
  return '调度员'
})

function goHome() {
  router.push(homeForCurrentUser())
}

function goLogin() {
  logout()
  router.replace('/login')
}

function signOut() {
  logout()
  router.replace('/login')
}
</script>
