import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { DashboardData, RagConfig, ModelConfig, QaLog, QaLogDetail } from '@/api/types'

export const useAdminStore = defineStore('admin', () => {
  const dashboard = ref<DashboardData | null>(null)
  const ragConfig = ref<RagConfig | null>(null)
  const models = ref<Record<'llm' | 'embedding' | 'vision' | 'rerank', Omit<ModelConfig, 'type'>> | null>(null)
  const qaLogs = ref<QaLog[]>([])
  const qaLogDetail = ref<QaLogDetail | null>(null)

  async function loadDashboard() { dashboard.value = await adminApi.fetchDashboard() }
  async function loadRagConfig() { ragConfig.value = await adminApi.fetchRagConfig() }
  async function loadModels() { models.value = await adminApi.fetchModels() }
  async function loadQaLogs(params: Parameters<typeof adminApi.listQaLogs>[0]) {
    const paged = await adminApi.listQaLogs(params)
    qaLogs.value = paged.items
    return paged
  }
  async function loadQaLogDetail(id: number) { qaLogDetail.value = await adminApi.getQaLog(id) }

  return {
    dashboard, ragConfig, models, qaLogs, qaLogDetail,
    loadDashboard, loadRagConfig, loadModels, loadQaLogs, loadQaLogDetail,
  }
})
