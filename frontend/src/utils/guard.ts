/** 路由守卫判定:纯函数,输入目标路由与登录态,输出重定向地址或 true(放行)。

 规则(对齐统一壳层设计 §5):
 - 公开页(/、/docs、/chat、/Login、/Initialize)直接放行;其中
   Login 已登录(且无需改密)→ 回 redirect 或 Dashboard;需改密 → /Initialize;
   Initialize 无 token → /Login,已登录但未触发改密 → /Dashboard
 - 管理页:无 token → /Login?redirect=当前页;强制改密中 → /Initialize
 */
export interface GuardTo {
  name?: string | null
  fullPath: string
  query: Record<string, unknown>
  meta: Record<string, unknown>
}

export interface GuardAuth {
  token: string | null
  mustChangePassword: boolean
}

/** 校验 redirect 参数仅限站内路径(防开放重定向):必须以 / 开头且非 //、/\ */
export function safeRedirect(value: unknown): string | null {
  if (typeof value !== 'string') return null
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return null
  return value
}

export function resolveGuard(to: GuardTo, auth: GuardAuth): string | true {
  if (to.meta.public) {
    if (to.name === 'Login') {
      if (auth.token && auth.mustChangePassword) return '/Initialize'
      if (auth.token) return safeRedirect(to.query.redirect) ?? '/Dashboard'
      return true
    }
    if (to.name === 'Initialize') {
      if (!auth.token) return '/Login'
      if (!auth.mustChangePassword) return '/Dashboard'
      return true
    }
    return true
  }
  if (!auth.token) return `/Login?redirect=${encodeURIComponent(to.fullPath)}`
  if (auth.mustChangePassword) return '/Initialize'
  return true
}
