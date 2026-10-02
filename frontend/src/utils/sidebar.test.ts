import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readSidebarCollapsed, writeSidebarCollapsed } from './sidebar'

/** 内存版 localStorage stub(node 环境无 localStorage) */
function stubStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial))
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  })
  return map
}

beforeEach(() => vi.unstubAllGlobals())
afterEach(() => vi.unstubAllGlobals())

describe('侧栏折叠持久化', () => {
  it('默认未折叠', () => {
    stubStorage()
    expect(readSidebarCollapsed()).toBe(false)
  })

  it('写入后可读回', () => {
    stubStorage()
    writeSidebarCollapsed(true)
    expect(readSidebarCollapsed()).toBe(true)
    writeSidebarCollapsed(false)
    expect(readSidebarCollapsed()).toBe(false)
  })

  it('可从既有存储恢复', () => {
    stubStorage({ sidebar_collapsed: '1' })
    expect(readSidebarCollapsed()).toBe(true)
  })

  it('localStorage 不可用时不抛错', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => { throw new Error('denied') },
      setItem: () => { throw new Error('denied') },
    })
    expect(() => writeSidebarCollapsed(true)).not.toThrow()
    expect(readSidebarCollapsed()).toBe(false)
  })
})
