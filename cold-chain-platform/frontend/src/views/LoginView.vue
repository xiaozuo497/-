<template>
  <main class="login-page">
    <section class="login-hero">
      <div class="login-copy">
        <div class="login-mark">冷</div>
        <p class="eyebrow">冷链调度指挥台</p>
        <h1>生鲜物流协同优化系统</h1>
        <p class="login-subtitle">把订单、路径、装箱、司机执行和班次复盘集中在一个本地化调度工作台。</p>
        <div class="login-stats">
          <span>时间窗路径优化</span>
          <span>三维装箱校验</span>
          <span>本地桌面部署</span>
        </div>
      </div>
      <el-card class="login-panel" shadow="never">
        <h2>登录</h2>
        <p>使用企业账号进入调度工作台</p>
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="账号">
            <el-input v-model="form.username" size="large" placeholder="请输入账号" autofocus />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              placeholder="请输入密码"
              show-password
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button type="primary" size="large" class="login-button" :loading="loading" @click="submit">
            进入系统
          </el-button>
        </el-form>
        <div class="login-accounts">
          <strong>测试账号</strong>
          <span>管理员：admin / admin123</span>
          <span>调度员：dispatcher / dispatch123</span>
          <span>仓库员：warehouse / warehouse123</span>
          <span>司机：driver / driver123</span>
        </div>
      </el-card>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { login } from '../api/auth'
import { homeForCurrentUser } from '../api/permissions'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = typeof router.currentRoute.value.query.redirect === 'string'
      ? router.currentRoute.value.query.redirect
      : homeForCurrentUser()
    await router.replace(redirect)
  } catch (error: unknown) {
    const status = typeof error === 'object' && error && 'response' in error
      ? (error as { response?: { status?: number } }).response?.status
      : undefined
    ElMessage.error(status === 401 ? '账号或密码错误' : '登录服务连接失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>
