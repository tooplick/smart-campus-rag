import client from './client.js'

export function listModels() {
  return client.get('/admin/models')
}

export function getModel(type) {
  return client.get(`/admin/models/${type}`)
}

export function updateModel(type, data) {
  return client.put(`/admin/models/${type}`, data)
}

export function testModel(type) {
  return client.post(`/admin/models/${type}/test`)
}
