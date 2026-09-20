function getClientId() {
  return localStorage.getItem('client_id') || ''
}

async function publicFetch(method, url, data = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Client-ID': getClientId() },
  }
  if (data) opts.body = JSON.stringify(data)
  const resp = await fetch(`/api${url}`, opts)
  return resp.json()
}

export function listConversations(page = 1, pageSize = 20) {
  return publicFetch('GET', `/conversations?page=${page}&page_size=${pageSize}`)
}

export function createConversation(knowledgeBaseId, title = '新对话') {
  return publicFetch('POST', '/conversations', { knowledge_base_id: knowledgeBaseId, title })
}

export function getConversation(id) {
  return publicFetch('GET', `/conversations/${id}`)
}

export function updateConversation(id, title) {
  return publicFetch('PATCH', `/conversations/${id}`, { title })
}

export function deleteConversation(id) {
  return publicFetch('DELETE', `/conversations/${id}`)
}
