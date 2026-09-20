import client from './client.js'

export async function listKnowledgeBasesPublic(page = 1, pageSize = 100) {
  const resp = await fetch(`/api/knowledge-bases?page=${page}&page_size=${pageSize}`)
  return resp.json()
}

export function listKnowledgeBases(page = 1, pageSize = 20) {
  return client.get('/knowledge-bases', { params: { page, page_size: pageSize } })
}

export function getKnowledgeBase(id) {
  return client.get(`/knowledge-bases/${id}`)
}

export function createKnowledgeBase(data) {
  return client.post('/knowledge-bases', data)
}

export function updateKnowledgeBase(id, data) {
  return client.put(`/knowledge-bases/${id}`, data)
}

export function deleteKnowledgeBase(id) {
  return client.delete(`/knowledge-bases/${id}`)
}
