import client from './client.js'

export function listQaLogs(page = 1, pageSize = 20, sortBy = 'created_at', sortOrder = 'desc') {
  return client.get('/admin/qa-logs', {
    params: { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder },
  })
}

export function getQaLogDetail(id) {
  return client.get(`/admin/qa-logs/${id}`)
}
