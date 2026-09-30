/** 登录 token 与匿名 client_id 的本地存取 */

const TOKEN_KEY = 'admin_token'
const CLIENT_KEY = 'client_id'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
export function getClientId(): string | null {
  return localStorage.getItem(CLIENT_KEY)
}
export function setClientId(id: string): void {
  localStorage.setItem(CLIENT_KEY, id)
}
