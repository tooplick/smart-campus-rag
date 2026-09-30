import { describe, expect, it } from 'vitest'
import { fileDownloadUrl } from './documents'

describe('fileDownloadUrl', () => {
  it('构造公开下载地址 /api/files/{id}', () => {
    expect(fileDownloadUrl(12)).toBe('/api/files/12')
    expect(fileDownloadUrl(1)).toBe('/api/files/1')
  })
})
