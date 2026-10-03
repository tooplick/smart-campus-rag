import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('渲染基础语法为 HTML', () => {
    const html = renderMarkdown('# 标题\n\n**粗体**')
    expect(html).toContain('<h1>')
    expect(html).toContain('<strong>粗体</strong>')
  })

  it('默认不处理引用标记', () => {
    expect(renderMarkdown('见 [来源 1]')).toContain('[来源 1]')
  })

  it('Chat 模式将 [来源 N] 渲染为引用角标', () => {
    const html = renderMarkdown('见 [来源 2] 与 [3]', true)
    expect(html).toContain('data-cite="2"')
    expect(html).toContain('data-cite="3"')
    expect(html).not.toContain('[来源 2]')
  })

  it('保留链接(单行与换行)', () => {
    expect(renderMarkdown('https://example.com')).toContain('href="https://example.com"')
    expect(renderMarkdown('第一行\n第二行')).toContain('<br')
  })
})
