import request from '@/utils/request'
import type { DocFile, DocStatus, Paged } from './types'

/** 文档列表(分页、可按知识库过滤/排序) */
export function listDocuments(params: {
  knowledge_base_id?: number
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}) {
  return request.get<unknown, Paged<DocFile>>('/documents', { params })
}

/** 文档详情 */
export function getDocument(id: number) {
  return request.get<unknown, DocFile>(`/documents/${id}`)
}

/** 轮询文档处理状态 */
export function getDocumentStatus(id: number) {
  return request.get<unknown, { id: number; status: DocStatus; progress: number; error_message: string | null }>(
    `/documents/${id}/status`,
  )
}

/** 上传文档(multipart 表单) */
export function uploadDocument(knowledgeBaseId: number, file: File) {
  const form = new FormData()
  form.append('knowledge_base_id', String(knowledgeBaseId))
  form.append('file', file)
  return request.post<unknown, { id: number; filename: string; status: DocStatus }>('/documents', form)
}

/** 删除文档(硬删除,含切片与向量) */
export function deleteDocument(id: number) {
  return request.delete<unknown, null>(`/documents/${id}`)
}

/** 重新处理文档 */
export function reprocessDocument(id: number) {
  return request.post<unknown, null>(`/documents/${id}/reprocess`)
}

/** 取消处理中的文档 */
export function cancelDocument(id: number) {
  return request.post<unknown, null>(`/documents/${id}/cancel`)
}

/** 原始文件下载地址（公开端点，无需鉴权） */
export function fileDownloadUrl(documentId: number): string {
  return `/api/files/${documentId}`
}

/** 下载原始文件并触发浏览器保存。失败时抛出错误，由调用方提示。 */
export async function downloadDocument(documentId: number, filename: string): Promise<void> {
  const resp = await fetch(fileDownloadUrl(documentId))
  if (!resp.ok) throw new Error(`下载失败:HTTP ${resp.status}`)
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 100)
}
