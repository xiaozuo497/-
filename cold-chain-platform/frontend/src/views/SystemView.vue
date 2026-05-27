<template>
  <AppShell>
    <div class="system-page">
      <div class="page-head">
        <div>
          <h1>数据安全中心</h1>
          <p>集中查看订单、车辆、数据库和备份状态，确保调度数据可追踪、可恢复。</p>
        </div>
        <div class="head-actions">
          <el-button @click="refresh">刷新</el-button>
          <el-button type="primary" :loading="creating" @click="createManualBackup">立即备份</el-button>
        </div>
      </div>

      <div class="health-panel" :class="backupHealth.type">
        <div>
          <span>数据保护状态</span>
          <strong>{{ backupHealth.title }}</strong>
          <p>{{ backupHealth.detail }}</p>
        </div>
        <el-tag :type="backupHealth.tagType" effect="plain">{{ backupHealth.tag }}</el-tag>
      </div>

      <div class="metric-grid">
        <el-card shadow="never">
          <span>数据库连接</span>
          <strong>{{ databaseText }}</strong>
          <small>运行环境：{{ diagnostics?.environment || '-' }}</small>
        </el-card>
        <el-card shadow="never">
          <span>订单数据</span>
          <strong>{{ diagnostics?.order_count ?? '-' }} 单</strong>
          <small>待调度 {{ diagnostics?.pending_order_count ?? 0 }} 单，异常 {{ diagnostics?.exception_order_count ?? 0 }} 单</small>
        </el-card>
        <el-card shadow="never">
          <span>车辆资源</span>
          <strong>{{ diagnostics?.available_vehicle_count ?? '-' }} / {{ diagnostics?.vehicle_count ?? '-' }} 辆</strong>
          <small>前者为可参与优化车辆</small>
        </el-card>
        <el-card shadow="never">
          <span>最近备份</span>
          <strong>{{ latestBackupMain }}</strong>
          <small>{{ latestBackupSub }}</small>
        </el-card>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="section-card">
            <template #header>备份策略</template>
            <div class="policy-list">
              <div>
                <strong>启动自动备份</strong>
                <span>每次后端服务启动前自动生成一份 JSON 数据备份。</span>
              </div>
              <div>
                <strong>手动关键备份</strong>
                <span>导入订单、调整车辆、运行优化前后，可手动生成恢复点。</span>
              </div>
              <div>
                <strong>恢复位置</strong>
                <span>{{ diagnostics?.backup_dir || 'backups' }}</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="16">
          <el-card shadow="never" class="section-card">
            <template #header>
              <div class="toolbar">
                <strong>备份记录</strong>
                <el-tag>{{ backups.length }} 个文件</el-tag>
              </div>
            </template>
            <el-table :data="backups" height="360" empty-text="暂无备份文件">
              <el-table-column prop="name" label="文件名" min-width="250" />
              <el-table-column label="大小" width="110">
                <template #default="{ row }">{{ formatSize(row.size) }}</template>
              </el-table-column>
              <el-table-column label="生成时间" width="190">
                <template #default="{ row }">{{ new Date(row.modified_at).toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="path" label="保存位置" min-width="260" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import AppShell from '../components/AppShell.vue'
import { createBackup, getDiagnostics, listBackups, type BackupFile, type Diagnostics } from '../api/orders'

const diagnostics = ref<Diagnostics | null>(null)
const backups = ref<BackupFile[]>([])
const creating = ref(false)

const latestBackup = computed(() => backups.value[0] || null)
const databaseText = computed(() => diagnostics.value?.database === 'ok' ? '正常' : diagnostics.value?.database || '-')

const latestBackupMain = computed(() => {
  if (!latestBackup.value) return '无'
  return new Date(latestBackup.value.modified_at).toLocaleDateString()
})

const latestBackupSub = computed(() => {
  if (!latestBackup.value) return '尚未生成备份'
  return `${new Date(latestBackup.value.modified_at).toLocaleTimeString()}，${formatSize(latestBackup.value.size)}`
})

const backupAgeHours = computed(() => {
  if (!latestBackup.value) return Number.POSITIVE_INFINITY
  return (Date.now() - new Date(latestBackup.value.modified_at).getTime()) / 1000 / 60 / 60
})

const backupHealth = computed(() => {
  if (diagnostics.value?.database !== 'ok') {
    return {
      type: 'danger',
      tagType: 'danger' as const,
      tag: '需处理',
      title: '数据库连接异常',
      detail: '系统无法确认当前业务数据状态，请先检查后端服务和数据库连接。',
    }
  }
  if (!backups.value.length) {
    return {
      type: 'warning',
      tagType: 'warning' as const,
      tag: '建议备份',
      title: '尚未找到备份文件',
      detail: '建议立即生成一份备份，作为当前订单和车辆数据的恢复点。',
    }
  }
  if (backupAgeHours.value > 24) {
    return {
      type: 'warning',
      tagType: 'warning' as const,
      tag: '备份偏旧',
      title: '最近备份已超过 24 小时',
      detail: '如果今天已经导入订单或调整车辆，建议重新生成备份。',
    }
  }
  return {
    type: 'success',
    tagType: 'success' as const,
    tag: '正常',
    title: '数据已有近期备份',
    detail: '数据库连接正常，最近备份可用于恢复当前业务数据。',
  }
})

function formatSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function refresh() {
  const [info, files] = await Promise.all([getDiagnostics(), listBackups()])
  diagnostics.value = info
  backups.value = files
}

async function createManualBackup() {
  creating.value = true
  try {
    await createBackup()
    await refresh()
    ElMessage.success('备份已生成')
  } finally {
    creating.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.system-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head,
.toolbar,
.health-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-head h1 {
  margin: 0;
  font-size: 28px;
}

.page-head p,
.health-panel p {
  margin: 8px 0 0;
  color: #64748b;
}

.head-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.health-panel {
  padding: 22px 26px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.health-panel strong {
  display: block;
  margin-top: 6px;
  font-size: 24px;
}

.health-panel.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.health-panel.warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.health-panel.danger {
  background: #fef2f2;
  border-color: #fecaca;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-grid :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-grid span,
.metric-grid small,
.policy-list span {
  color: #64748b;
}

.metric-grid strong {
  font-size: 24px;
}

.section-card {
  border-radius: 8px;
}

.policy-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.policy-list div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

@media (max-width: 960px) {
  .page-head,
  .health-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
