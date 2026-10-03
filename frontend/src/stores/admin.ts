import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { DashboardData, RagConfig, ModelProfiles, QaLog, QaLogDetail } from '@/api/types'

export const useAdminStore = defineStore('admin', () => {
  const dashboard = ref<DashboardData | null>(null)
  const ragConfig = ref<RagConfig | null>(null)
  /** 四类模型配置清单(启用指针 + profiles),设置页读写配置文件 */
  const modelProfiles = ref<ModelProfiles | null>(null)
  const qaLogs = ref<QaLog[]>([])
  const qaLogDetail = ref<QaLogDetail | null>(null)

  async function loadDashboard() { dashboard.value = await adminApi.fetchDashboard() }
  async function loadRagConfig() { ragConfig.value = await adminApi.fetchRagConfig() }
  async function loadModelProfiles() { modelProfiles.value = await adminApi.fetchModelProfiles() }
  async function loadQaLogs(params: Parameters<typeof adminApi.listQaLogs>[0]) {
    const paged = await adminApi.listQaLogs(params)
    qaLogs.value = paged.items
    return paged
  }
  async function loadQaLogDetail(id: number) { qaLogDetail.value = await adminApi.getQaLog(id) }

  return {
    dashboard, ragConfig, modelProfiles, qaLogs, qaLogDetail,
    loadDashboard, loadRagConfig, loadModelProfiles, loadQaLogs, loadQaLogDetail,
  }
})
