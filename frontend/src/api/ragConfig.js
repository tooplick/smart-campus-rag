import client from './client.js'

export function getRagConfig() {
  return client.get('/admin/rag-config')
}

export function updateRagConfig(data) {
  return client.put('/admin/rag-config', data)
}
