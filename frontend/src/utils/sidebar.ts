/** 侧栏折叠偏好持久化:localStorage 键统一在此管理,读写容错(localStorage 可能不可用)。 */
const KEY = 'sidebar_collapsed'

export function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

export function writeSidebarCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(KEY, collapsed ? '1' : '0')
  } catch {
    /* 隐私模式等场景写入失败:忽略,仅本次会话生效 */
  }
}
