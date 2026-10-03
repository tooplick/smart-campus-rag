import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { normalizeError, ApiError, errorMessage, jsonFetch } from './request'

describe('normalizeError', () => {
  it('识别业务错误包装', () => {
    const err = normalizeError(400, {
      success: false, data: null, message: '知识库正在建立索引',
      error: { code: 'INVALID_KNOWLEDGE_BASE' },
    })
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe('INVALID_KNOWLEDGE_BASE')
    expect(err.message).toBe('知识库正在建立索引')
  })

  it('识别 FastAPI 默认 detail(字符串)', () => {
    const err = normalizeError(401, { detail: 'Not authenticated' })
    expect(err.code).toBe('HTTP_401')
    expect(err.message).toBe('Not authenticated')
  })

  it('识别 FastAPI 422 detail(数组)', () => {
    const err = normalizeError(422, { detail: [{ msg: 'field required' }] })
    expect(err.code).toBe('HTTP_422')
    expect(err.message).toContain('field required')
  })

  it('未知形态兜底', () => {
    const err = normalizeError(500, 'boom')
    expect(err.code).toBe('HTTP_500')
  })
})

describe('errorMessage', () => {
  it('映射常见错误码', () => {
    // RAG_NOT_READY 等细化码不再走码表:后端返回的定位到模型配置的详细文案直接透传
    expect(errorMessage(new ApiError('RAG 管道未就绪:请到「设置 → 模型配置」启用完整配置', 'RAG_NOT_READY', 503)))
      .toBe('RAG 管道未就绪:请到「设置 → 模型配置」启用完整配置')
  })
  it('无映射时回退原始消息', () => {
    expect(errorMessage(new ApiError('原始消息', 'UNKNOWN_X', 500))).toBe('原始消息')
  })
})

describe('jsonFetch', () => {
  beforeEach(() => {
    // node 环境没有 localStorage,注入最小 stub 供 getClientId 读取
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('成功解包 {success:true,data}', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ success: true, data: { id: 1 }, message: 'ok' }), { status: 200 }),
    ))
    const data = await jsonFetch<{ id: number }>('conversations')
    expect(data).toEqual({ id: 1 })
  })

  it('业务错误 reject ApiError(code 取 error.code)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        success: false,
        data: null,
        message: '会话不存在或已删除',
        error: { code: 'CONVERSATION_NOT_FOUND' },
      }), { status: 404 }),
    ))
    const err = await jsonFetch('conversations/x').then(() => null, (e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('CONVERSATION_NOT_FOUND')
    expect((err as ApiError).message).toBe('会话不存在或已删除')
  })

  it('网络异常 reject NETWORK_ERROR', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fetch failed')))
    const err = await jsonFetch('conversations').then(() => null, (e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('NETWORK_ERROR')
  })

  it('路径拼接统一为 /api/ 前缀', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ success: true, data: [] }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await jsonFetch('conversations')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/conversations')
    await jsonFetch('/conversations/1')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/conversations/1')
  })
})
