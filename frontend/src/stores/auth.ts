import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as authApi from '@/api/auth'
import { getToken, setToken, clearToken } from '@/utils/auth'
import type { LoginResult } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const username = ref('')
  const mustChangePassword = ref(false)

  function applyLogin(result: LoginResult) {
    token.value = result.token
    setToken(result.token)
    username.value = result.admin.username
    mustChangePassword.value = result.must_change_password
  }

  async function login(u: string, p: string) {
    applyLogin(await authApi.login(u, p))
  }

  async function initialize(u: string, current: string, next: string) {
    applyLogin(await authApi.initialize(u, current, next))
  }

  async function fetchMe() {
    const me = await authApi.fetchMe()
    username.value = me.username
    mustChangePassword.value = me.must_change_password
  }

  async function logout() {
    try { await authApi.logout() } catch { /* token 无状态,失败也照常本地登出 */ }
    token.value = null
    username.value = ''
    mustChangePassword.value = false
    clearToken()
  }

  return { token, username, mustChangePassword, login, initialize, fetchMe, logout }
})
