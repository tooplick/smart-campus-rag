/** Docs 页目录生成:由 import.meta.glob 得到的 md 文件清单构造目录(排序 + 标题提取)。

 文件名约定:`NN-slug.md`(数字前缀控制顺序,slug 用于锚定)。
 标题优先取首个一级标题,缺失时回退文件名;纯函数,便于 vitest 覆盖。
 */
export interface DocEntry {
  /** 路由锚点用的 slug(去序号与扩展名) */
  slug: string
  /** 目录展示标题 */
  title: string
  /** 正文(markdown 源文) */
  content: string
}

const FILE_RE = /([^/]+)\.md$/

/** 从 glob 结果(path → raw 内容)生成按序号升序的目录 */
export function buildDocCatalog(files: Record<string, string>): DocEntry[] {
  return Object.entries(files)
    // 先按原文件名排序(保留 NN- 序号作为排序键),再映射为目录项
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([path, content]) => {
      const name = FILE_RE.exec(path)?.[1] ?? path
      const slug = name.replace(/^\d+[-_]/, '')
      const title = /^#\s+(.+)$/m.exec(content)?.[1]?.trim() || name
      return { slug, title, content }
    })
}

/** 按 slug 取目录项(缺项返回 null) */
export function findDoc(catalog: DocEntry[], slug: string | null): DocEntry | null {
  if (!slug) return null
  return catalog.find((d) => d.slug === slug) ?? null
}
