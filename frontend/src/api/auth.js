import client from './client.js'

export function login(username, password) {
  return client.post('/auth/login', { username, password })
}

export function initialize(username, currentPassword, newPassword) {
  return client.post('/auth/initialize', {
    username,
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export function getMe() {
  return client.get('/auth/me')
}

export function logout() {
  return client.post('/auth/logout')
}

export function changePassword(oldPassword, newPassword) {
  return client.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}
