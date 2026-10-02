import { describe, expect, it } from 'vitest'
import { buildDocCatalog, findDoc } from './docs'

const files = {
  '/src/docs/03-api.md': '# API 参考\n\n内容',
  '/src/docs/01-getting-started.md': '# 快速开始\n\n内容',
  '/src/docs/02-architecture.md': '没有一级标题的正文',
}

describe('buildDocCatalog', () => {
  it('按文件名序号升序排序', () => {
    expect(buildDocCatalog(files).map((d) => d.slug)).toEqual(['getting-started', 'architecture', 'api'])
  })

  it('标题取首个一级标题', () => {
    expect(buildDocCatalog(files)[0].title).toBe('快速开始')
  })

  it('缺失一级标题时回退文件名(不含序号)', () => {
    expect(buildDocCatalog(files)[1].title).toBe('02-architecture')
  })

  it('保留正文内容', () => {
    expect(buildDocCatalog(files)[2].content).toContain('# API 参考')
  })

  it('空清单返回空数组', () => {
    expect(buildDocCatalog({})).toEqual([])
  })
})

describe('findDoc', () => {
  it('按 slug 命中', () => {
    const catalog = buildDocCatalog(files)
    expect(findDoc(catalog, 'api')?.title).toBe('API 参考')
  })
  it('空 slug 与未命中均返回 null', () => {
    const catalog = buildDocCatalog(files)
    expect(findDoc(catalog, null)).toBeNull()
    expect(findDoc(catalog, 'nope')).toBeNull()
  })
})
