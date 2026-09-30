import { jsonFetch } from '@/utils/request'
import type { Paged, ConversationSummary, ConversationDetail } from './types'

/** 获取/创建匿名 client_id */
export function fetchSession() {
  return jsonFetch<{ client_id: string }>('/chat/session')
}

/** 会话列表(分页,X-Client-ID 归属过滤) */
export function listConversations(page = 1, pageSize = 50) {
  return jsonFetch<Paged<ConversationSummary>>(`/conversations?page=${page}&page_size=${pageSize}`)
}

/** 创建会话 */
export function createConversation(body: { knowledge_base_id?: number | null; title?: string }) {
  return jsonFetch<{ id: string; knowledge_base_id: number | null; title: string }>(
    '/conversations', { method: 'POST', body: JSON.stringify(body) },
  )
}

/** 会话详情(含历史消息) */
export function getConversation(id: string) {
  return jsonFetch<ConversationDetail>(`/conversations/${id}`)
}

/** 重命名会话 */
export function renameConversation(id: string, title: string) {
  return jsonFetch<{ id: string; title: string }>(
    `/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) },
  )
}

/** 删除会话(软删除) */
export function deleteConversation(id: string) {
  return jsonFetch<null>(`/conversations/${id}`, { method: 'DELETE' })
}
