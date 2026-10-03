import { describe, expect, it } from 'vitest'
import { resolveGuard, safeRedirect } from './guard'

/** 构造守卫输入:默认管理页,可覆盖 */
function to(over: Partial<Parameters<typeof resolveGuard>[0]> = {}) {
  return {
    name: 'Dashboard',
    fullPath: '/Documents?kb=1',
    query: {},
    meta: {},
    ...over,
  }
}

const guest = { token: null, mustChangePassword: false }
const admin = { token: 't', mustChangePassword: false }
const mustChange = { token: 't', mustChangePassword: true }

describe('safeRedirect', () => {
  it('放行站内路径', () => {
    expect(safeRedirect('/Dashboard')).toBe('/Dashboard')
    expect(safeRedirect('/chat?x=1')).toBe('/chat?x=1')
  })
  it('拒绝站外与协议相对路径', () => {
    expect(safeRedirect('https://evil.com')).toBeNull()
    expect(safeRedirect('//evil.com')).toBeNull()
    expect(safeRedirect('/\\evil.com')).toBeNull()
    expect(safeRedirect(undefined)).toBeNull()
  })
})

describe('resolveGuard 管理页', () => {
  it('访客访问管理页 → 登录并带回跳参数', () => {
    expect(resolveGuard(to(), guest)).toBe(`/Login?redirect=${encodeURIComponent('/Documents?kb=1')}`)
  })
  it('已登录放行', () => {
    expect(resolveGuard(to(), admin)).toBe(true)
  })
  it('强制改密期间 → /Initialize', () => {
    expect(resolveGuard(to(), mustChange)).toBe('/Initialize')
  })
})

describe('resolveGuard 公开页', () => {
  it('Home/Docs/Chat 免登录放行', () => {
    for (const name of ['Home', 'Docs', 'Chat']) {
      expect(resolveGuard(to({ name, meta: { public: true } }), guest)).toBe(true)
    }
  })
  it('Login 已登录 → 回 redirect(校验后)', () => {
    expect(resolveGuard(to({ name: 'Login', meta: { public: true }, query: { redirect: '/QaLogs' } }), admin))
      .toBe('/QaLogs')
    expect(resolveGuard(to({ name: 'Login', meta: { public: true }, query: { redirect: 'https://evil.com' } }), admin))
      .toBe('/Dashboard')
    expect(resolveGuard(to({ name: 'Login', meta: { public: true } }), admin)).toBe('/Dashboard')
  })
  it('Login 需改密 → /Initialize;访客 → 放行', () => {
    expect(resolveGuard(to({ name: 'Login', meta: { public: true } }), mustChange)).toBe('/Initialize')
    expect(resolveGuard(to({ name: 'Login', meta: { public: true } }), guest)).toBe(true)
  })
  it('Initialize 无 token → /Login;已登录未触发改密 → /Dashboard;改密中放行', () => {
    expect(resolveGuard(to({ name: 'Initialize', meta: { public: true } }), guest)).toBe('/Login')
    expect(resolveGuard(to({ name: 'Initialize', meta: { public: true } }), admin)).toBe('/Dashboard')
    expect(resolveGuard(to({ name: 'Initialize', meta: { public: true } }), mustChange)).toBe(true)
  })
})
