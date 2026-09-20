import client from './client.js'

export function listDocuments(knowledgeBaseId = null, page = 1, pageSize = 20, sortBy = 'created_at', sortOrder = 'desc') {
  const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder }
  if (knowledgeBaseId) params.knowledge_base_id = knowledgeBaseId
  return client.get('/documents', { params })
}

export function getDocument(id) {
  return client.get(`/documents/${id}`)
}

export function getDocumentStatus(id) {
  return client.get(`/documents/${id}/status`)
}

export function uploadDocument(knowledgeBaseId, file) {
  const formData = new FormData()
  formData.append('knowledge_base_id', knowledgeBaseId)
  formData.append('file', file)
  return client.post('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(id) {
  return client.delete(`/documents/${id}`)
}

export function reprocessDocument(id) {
  return client.post(`/documents/${id}/reprocess`)
}

export function cancelDocument(id) {
  return client.post(`/documents/${id}/cancel`)
}
