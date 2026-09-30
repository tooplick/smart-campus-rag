import request from '@/utils/request'
import type { KnowledgeBase, Paged } from './types'

/** 知识库列表(分页) */
export function listKnowledgeBases(page = 1, pageSize = 100) {
  return request.get<unknown, Paged<KnowledgeBase>>('/knowledge-bases', {
    params: { page, page_size: pageSize },
  })
}

/** 知识库详情 */
export function getKnowledgeBase(id: number) {
  return request.get<unknown, KnowledgeBase>(`/knowledge-bases/${id}`)
}

/** 创建知识库 */
export function createKnowledgeBase(body: { name: string; description?: string; icon?: string }) {
  return request.post<unknown, KnowledgeBase>('/knowledge-bases', body)
}

/** 更新知识库 */
export function updateKnowledgeBase(id: number, body: {
  name?: string; description?: string; icon?: string; is_enabled?: boolean
}) {
  return request.put<unknown, KnowledgeBase>(`/knowledge-bases/${id}`, body)
}

/** 删除知识库(硬删除) */
export function deleteKnowledgeBase(id: number) {
  return request.delete<unknown, null>(`/knowledge-bases/${id}`)
}
