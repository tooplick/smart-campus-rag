import { describe, it, expect } from 'vitest'
import { formatFileSize, formatDuration, formatTime } from './format'

describe('formatFileSize', () => {
  it('按单位换算', () => {
    expect(formatFileSize(0)).toBe('0 B')
    expect(formatFileSize(1024)).toBe('1.0 KB')
    expect(formatFileSize(1024 * 1024 * 3.5)).toBe('3.5 MB')
    expect(formatFileSize(-1)).toBe('—')
  })

  it('null/undefined 返回占位符', () => {
    expect(formatFileSize(null)).toBe('—')
    expect(formatFileSize(undefined)).toBe('—')
    expect(formatFileSize(Number.NaN)).toBe('—')
  })
})

describe('formatDuration', () => {
  it('毫秒与秒两种呈现', () => {
    expect(formatDuration(850)).toBe('850 ms')
    expect(formatDuration(1200)).toBe('1.2 s')
    expect(formatDuration(null)).toBe('—')
    expect(formatDuration(Number.NaN)).toBe('—')
  })
})

describe('formatTime', () => {
  it('非法输入返回占位符', () => {
    expect(formatTime(null)).toBe('—')
  })

  it('合法输入输出 YYYY-MM-DD HH:mm', () => {
    // 用本地时间构造,再经 ISO 字符串往返,formatTime 以本地时区解析应还原
    const d = new Date(2026, 8, 30, 14, 5) // 2026-09-30 14:05
    const out = formatTime(d.toISOString())
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    expect(out).toContain('2026-09-30')
  })
})
