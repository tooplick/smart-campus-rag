/** 全局 API 数据类型 */
import type { ChatSource } from '@/utils/sse'

/**
 * 引用来源(问答溯源 / QA 日志来源)。
 * 与 SSE 的 ChatSource 字段完全一致,直接复用别名消除重复定义。
 */
export type Source = ChatSource

/** 分页包装结构 */
export interface Paged<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

/** 知识库 */
export interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  icon: string | null
  is_enabled: boolean
  chunk_template: string
  document_count: number
  chunk_count: number
  created_at: string
  updated_at: string
}

/** 文档处理状态 */
export type DocStatus = 'pending' | 'processing' | 'completed' | 'failed'

/** 文档 */
export interface DocFile {
  id: number
  knowledge_base_id: number
  filename: string
  file_type: string
  mime_type: string
  file_size: number
  page_count: number | null
  image_count: number | null
  chunk_count: number
  status: DocStatus
  progress: number
  error_message: string | null
  processed_at: string | null
  created_at: string
  updated_at: string
}

/** 会话摘要(列表用) */
export interface ConversationSummary {
  id: string
  knowledge_base_id: number | null
  title: string
  created_at: string
  updated_at: string
}

/** 会话内历史消息 */
export interface HistoryMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/** 会话详情(含历史消息) */
export interface ConversationDetail extends ConversationSummary {
  messages: HistoryMessage[]
}

/** 登录结果 */
export interface LoginResult {
  token: string
  token_type: string
  admin: { username: string }
  must_change_password: boolean
}

/** 管理员信息 */
export interface AdminInfo {
  username: string
  must_change_password: boolean
}

/** 仪表盘数据 */
export interface DashboardData {
  statistics: { knowledge_base_count: number; document_count: number; chunk_count: number; qa_count: number }
  qa_trend: { date: string; count: number }[]
  document_status: { pending: number; processing: number; completed: number; failed: number }
  knowledge_base_distribution: { id: number; name: string; document_count: number }[]
}

/** RAG 管线参数 */
export interface RagConfig {
  chunk_size: number
  chunk_overlap: number
  candidate_top_k: number
  final_top_k: number
  similarity_threshold: number
  vector_weight: number
  auto_keywords: number
  auto_questions: number
  temperature: number
  max_tokens: number
}

/** 模型连通性测试结果 */
export interface ModelTestResult {
  status: 'ok' | 'error'
  model: string
  latency_ms: number | null
  dimension: number | null
}

/** 单个模型配置(api_key 不回传,仅标记是否已配置) */
export interface ModelProfile {
  base_url: string
  model: string
  api_key_configured: boolean
}

/** 单类型( llm/embedding/vision/rerank)的配置组:启用指针 + 配置清单 */
export interface ModelProfileGroup {
  active: string | null
  profiles: Record<string, ModelProfile>
}

/** 四类模型的配置总览 */
export type ModelProfiles = Record<ModelType, ModelProfileGroup>

/** 模型类型 */
export type ModelType = 'llm' | 'embedding' | 'vision' | 'rerank'

/** QA 日志(列表用) */
export interface QaLog {
  id: number
  conversation_id: string
  question: string
  answer: string
  knowledge_base_id: number | null
  model_name: string | null
  status: string
  latency_ms: number | null
  total_tokens: number | null
  created_at: string
}

/** QA 日志详情(含 RAG 参数、检索/LLM 耗时、来源) */
export interface QaLogDetail extends QaLog {
  turn_index: number
  error_message: string | null
  rag: { candidate_top_k: number; final_top_k: number; similarity_threshold: number }
  retrieval: { count: number; latency_ms: number | null }
  llm: { latency_ms: number | null }
  latency: { total_ms: number | null }
  tokens: { prompt: number | null; completion: number | null; total: number | null }
  sources: Source[]
}
