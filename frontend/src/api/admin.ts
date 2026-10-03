import request from '@/utils/request'
import type {
  DashboardData, RagConfig, ModelProfiles, ModelProfile, ModelType,
  ModelTestResult, QaLog, QaLogDetail, Paged,
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
  vector_weight?: number; auto_keywords?: number; auto_questions?: number
  temperature?: number; max_tokens?: number
  embedding_batch_size?: number; embedding_max_retries?: number
  llm_max_retries?: number; request_timeout?: number
}) {
  return request.put<unknown, RagConfig>('/admin/rag-config', body)
}

/** 获取四类模型配置清单(含启用指针,api_key 只回传是否已配置) */
export function fetchModelProfiles() {
  return request.get<unknown, ModelProfiles>('/admin/model-profiles')
}

/** 新增配置;该类型尚无启用配置时自动启用 */
export function createModelProfile(body: {
  type: ModelType; name: string; base_url: string; api_key: string; model: string
}) {
  return request.post<unknown, ModelProfile>('/admin/model-profiles', body)
}

/** 修改配置(api_key 留空表示不改) */
export function updateModelProfile(type: ModelType, name: string, body: {
  base_url?: string; api_key?: string; model?: string
}) {
  return request.put<unknown, ModelProfile>(`/admin/model-profiles/${type}/${encodeURIComponent(name)}`, body)
}

/** 删除配置(启用中的配置会被后端拒绝) */
export function deleteModelProfile(type: ModelType, name: string) {
  return request.delete<unknown, null>(`/admin/model-profiles/${type}/${encodeURIComponent(name)}`)
}

/** 切换启用配置;name 传 null 表示停用(仅 vision/rerank 允许) */
export function setActiveModelProfile(type: ModelType, name: string | null) {
  return request.put<unknown, ModelProfile>('/admin/model-profiles/active', { type, name })
}

/** 测试模型连通性;name 缺省测当前启用配置 */
export function testModel(type: ModelType, name?: string) {
  return request.post<unknown, ModelTestResult>(`/admin/models/${type}/test`, name ? { name } : undefined)
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
