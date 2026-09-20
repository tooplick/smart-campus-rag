import client from './client.js'

export function getDashboard() {
  return client.get('/admin/dashboard')
}
