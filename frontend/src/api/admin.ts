import request from '@/utils/request'
import type {
  DashboardData, RagConfig, ModelConfig, ModelTestResult, QaLog, QaLogDetail, Paged,
} from './types'

/** 仪表盘统计数据 */
export function fetchDashboard() {
  return request.get<unknown, DashboardData>('/admin/dashboard')
}

/** 获取 RAG 配置 */
export function fetchRagConfig() {
  return request.get<unknown, RagConfig>('/admin/rag-config')
}

/** 保存 RAG 配置(局部更新) */
export function saveRagConfig(body: {
  chunk_size?: number; chunk_overlap?: number
  candidate_top_k?: number; final_top_k?: number; similarity_threshold?: number
}) {
  return request.put<unknown, RagConfig>('/admin/rag-config', body)
}

/** 获取三类模型配置(不含 api_key 明文) */
export function fetchModels() {
  return request.get<unknown, Record<'llm' | 'embedding' | 'vision', Omit<ModelConfig, 'type'>>>(
    '/admin/models',
  )
}

/** 更新模型配置(api_key 传入则覆盖) */
export function updateModel(type: string, body: {
  base_url?: string; api_key?: string; model?: string; enabled?: boolean
}) {
  return request.put<unknown, ModelConfig>(`/admin/models/${type}`, body)
}

/** 测试模型连通性 */
export function testModel(type: string) {
  return request.post<unknown, ModelTestResult>(`/admin/models/${type}/test`)
}

/** QA 日志列表(分页、可排序) */
export function listQaLogs(params: {
  page?: number; page_size?: number; sort_by?: string; sort_order?: 'asc' | 'desc'
}) {
  return request.get<unknown, Paged<QaLog>>('/admin/qa-logs', { params })
}

/** QA 日志详情(含 RAG 参数、检索详情、来源) */
export function getQaLog(id: number) {
  return request.get<unknown, QaLogDetail>(`/admin/qa-logs/${id}`)
}
