import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDashboard } from '@/api/dashboard.js'
import { getRagConfig, updateRagConfig } from '@/api/ragConfig.js'
import { listModels, updateModel, testModel } from '@/api/models.js'
import { listQaLogs, getQaLogDetail } from '@/api/qaLogs.js'

export const useAdminStore = defineStore('admin', () => {
  const dashboard = ref(null)
  const ragConfig = ref(null)
  const modelConfigs = ref(null)
  const qaLogs = ref([])
  const qaLogsTotal = ref(0)

  async function loadDashboard() {
    const res = await getDashboard()
    if (res.success) dashboard.value = res.data
    return res
  }

  async function loadRagConfig() {
    const res = await getRagConfig()
    if (res.success) ragConfig.value = res.data
    return res
  }

  async function saveRagConfig(data) {
    const res = await updateRagConfig(data)
    if (res.success) ragConfig.value = res.data
    return res
  }

  async function loadModels() {
    const res = await listModels()
    if (res.success) modelConfigs.value = res.data
    return res
  }

  async function saveModel(type, data) {
    return await updateModel(type, data)
  }

  async function doTestModel(type) {
    return await testModel(type)
  }

  async function loadQaLogs(page = 1, pageSize = 20) {
    const res = await listQaLogs(page, pageSize)
    if (res.success) {
      qaLogs.value = res.data.items || []
      qaLogsTotal.value = res.data.total || 0
    }
    return res
  }

  async function loadQaLogDetail(id) {
    return await getQaLogDetail(id)
  }

  return {
    dashboard, ragConfig, modelConfigs, qaLogs, qaLogsTotal,
    loadDashboard, loadRagConfig, saveRagConfig,
    loadModels, saveModel, doTestModel,
    loadQaLogs, loadQaLogDetail,
  }
})
