/** Markdown 渲染包装:集中 markdown-it 实例与引用角标高亮,供 Chat 与 Docs 复用。 */
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ breaks: true, linkify: true })

/** 将回答中的 [来源 N] / [N] 标记渲染为引用角标 */
export function highlightMarkers(html: string): string {
  return html.replace(
    /\[(\d+|来源\s*\d+)\]/g,
    (_m, p1: string) => {
      const n = (p1.match(/\d+/) ?? [''])[0]
      return `<sup class="ml-0.5 rounded bg-accent px-1 text-xs text-accent-foreground" data-cite="${n}">${n}</sup>`
    },
  )
}

/** markdown 源文 → HTML;highlightMarkers=true 时对 [来源 N] 打角标(Chat 场景) */
export function renderMarkdown(source: string, highlightMarkersEnabled = false): string {
  const html = md.render(source)
  return highlightMarkersEnabled ? highlightMarkers(html) : html
}
