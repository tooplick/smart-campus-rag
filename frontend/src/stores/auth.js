import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('admin_token') || '')
  const admin = ref(JSON.parse(localStorage.getItem('admin_user') || 'null'))
  const mustChangePassword = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  function setAuth(tokenVal, adminInfo, mustChange) {
    token.value = tokenVal
    admin.value = adminInfo
    mustChangePassword.value = mustChange
    localStorage.setItem('admin_token', tokenVal)
    localStorage.setItem('admin_user', JSON.stringify(adminInfo))
  }

  function clearAuth() {
    token.value = ''
    admin.value = null
    mustChangePassword.value = false
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
  }

  async function login(username, password) {
    const res = await authApi.login(username, password)
    if (res.success) {
      setAuth(res.data.token, res.data.admin, res.data.must_change_password)
    }
    return res
  }

  async function initialize(username, currentPassword, newPassword) {
    const res = await authApi.initialize(username, currentPassword, newPassword)
    if (res.success) {
      setAuth(res.data.token, res.data.admin, res.data.must_change_password)
    }
    return res
  }

  async function fetchMe() {
    try {
      const res = await authApi.getMe()
      if (res.success) {
        mustChangePassword.value = res.data.must_change_password
      }
      return res
    } catch {
      clearAuth()
      return null
    }
  }

  async function logout() {
    try { await authApi.logout() } catch {}
    clearAuth()
  }

  return { token, admin, mustChangePassword, isAuthenticated, setAuth, clearAuth, login, initialize, fetchMe, logout }
})
