import request from '@/utils/request'
import type { LoginResult, AdminInfo } from './types'

/** 管理员登录 */
export function login(username: string, password: string) {
  return request.post<unknown, LoginResult>('/auth/login', { username, password })
}

/** 初始化(或重置)管理员账号并登录 */
export function initialize(username: string, currentPassword: string, newPassword: string) {
  return request.post<unknown, LoginResult>('/auth/initialize', {
    username, current_password: currentPassword, new_password: newPassword,
  })
}

/** 获取当前管理员信息 */
export function fetchMe() {
  return request.get<unknown, AdminInfo>('/auth/me')
}

/** 退出登录 */
export function logout() {
  return request.post<unknown, null>('/auth/logout')
}

/** 修改密码 */
export function changePassword(oldPassword: string, newPassword: string) {
  return request.post<unknown, null>('/auth/change-password', {
    old_password: oldPassword, new_password: newPassword,
  })
}
