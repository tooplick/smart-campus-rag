import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { streamChat, type ChatStreamHandlers, type ChatSource } from './sse'
import { ApiError } from './request'

/** 构造按块拉取的 SSE 二进制流 */
function streamOf(...chunks: string[]) {
  const encoder = new TextEncoder()
  let i = 0
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < chunks.length) controller.enqueue(encoder.encode(chunks[i++]))
      else controller.close()
    },
  })
}

/** handlers 骨架:默认各回调为空实现,可局部覆盖 */
function makeHandlers(overrides: Partial<ChatStreamHandlers> = {}): ChatStreamHandlers {
  return {
    onStart: vi.fn(),
    onToken: vi.fn(),
    onSources: vi.fn(),
    onDone: vi.fn(),
    onError: vi.fn(),
    ...overrides,
  }
}

/** 捕获 reject 值(不用 rejects 断言,便于与 onError 实参做同一性比较) */
function captureRejection(p: Promise<void>): Promise<unknown> {
  return p.then(() => null, (e) => e)
}

describe('streamChat', () => {
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

  it('正常流:start→token→sources→done,各回调载荷正确并 resolve', async () => {
    const source: ChatSource = {
      chunk_id: 'c1',
      document_id: 1,
      filename: 'a.pdf',
      page_number: 2,
      section_title: null,
      content: '片段',
      similarity_score: 0.9,
      source_order: 1,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(streamOf(
      'event: start\ndata: {"message_id":"m1","conversation_id":"conv1"}\n\n',
      'event: token\ndata: {"content":"你"}\n\n',
      'event: token\ndata: {"content":"好"}\n\n',
      'event: sources\ndata: {"sources":[{"chunk_id":"c1","document_id":1,"filename":"a.pdf","page_number":2,"section_title":null,"content":"片段","similarity_score":0.9,"source_order":1}]}\n\n',
      'event: done\ndata: {"qa_record_id":7,"conversation_id":"conv1","message_id":"m1"}\n\n',
    ), { status: 200 })))
    const h = makeHandlers()
    await expect(streamChat({ message: '你好' }, h)).resolves.toBeUndefined()
    expect(h.onStart).toHaveBeenCalledWith({ message_id: 'm1', conversation_id: 'conv1' })
    expect(h.onToken).toHaveBeenNthCalledWith(1, { content: '你' })
    expect(h.onToken).toHaveBeenNthCalledWith(2, { content: '好' })
    expect(h.onSources).toHaveBeenCalledWith({ sources: [source] })
    expect(h.onDone).toHaveBeenCalledWith({ qa_record_id: 7, conversation_id: 'conv1', message_id: 'm1' })
    expect(h.onError).not.toHaveBeenCalled()
  })

  it('收到 error 事件:onError 收到 ApiError,Promise 以同一对象 reject', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(streamOf(
      'event: token\ndata: {"content":"部分"}\n\n',
      'event: error\ndata: {"code":"LLM_ERROR","message":"模型服务出错"}\n\n',
    ), { status: 200 })))
    const onError = vi.fn()
    const rejected = await captureRejection(streamChat({ message: '你好' }, makeHandlers({ onError })))
    expect(onError).toHaveBeenCalledTimes(1)
    const err = onError.mock.calls[0][0] as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe('LLM_ERROR')
    expect(err.message).toBe('模型服务出错')
    expect(err.status).toBe(200)
    expect(rejected).toBe(err) // onError 实参与 reject 值是同一个错误对象
  })

  it('断流(无 done 无 error):reject STREAM_INTERRUPTED', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(streamOf(
      'event: start\ndata: {"message_id":"m1","conversation_id":"conv1"}\n\n',
      'event: token\ndata: {"content":"部分回答"}\n\n',
    ), { status: 200 })))
    const h = makeHandlers()
    const err = await captureRejection(streamChat({ message: '你好' }, h)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe('STREAM_INTERRUPTED')
    expect(h.onDone).not.toHaveBeenCalled()
    expect(h.onError).not.toHaveBeenCalled()
  })

  it('初始响应非 2xx 且业务错误包装:reject ApiError,code 取 error.code', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      success: false,
      data: null,
      message: '知识库尚未就绪',
      error: { code: 'RAG_NOT_READY' },
    }), { status: 503 })))
    const err = await captureRejection(streamChat({ message: '你好' }, makeHandlers())) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe('RAG_NOT_READY')
    expect(err.message).toBe('知识库尚未就绪')
  })

  it('读流中途网络异常:包成 NETWORK_ERROR(不泄漏裸 TypeError)', async () => {
    const encoder = new TextEncoder()
    let i = 0
    const bad = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i++ === 0) controller.enqueue(encoder.encode('event: token\ndata: {"content":"a"}\n\n'))
        else controller.error(new TypeError('network reset'))
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(bad, { status: 200 })))
    const err = await captureRejection(streamChat({ message: '你好' }, makeHandlers()))
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).code).toBe('NETWORK_ERROR')
  })

  it('初始 fetch 的 AbortError 原样透传', async () => {
    const abortErr = new DOMException('The operation was aborted.', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortErr))
    const err = await captureRejection(streamChat({ message: '你好' }, makeHandlers()))
    expect(err).toBe(abortErr)
  })

  it('读流中途 AbortError 原样透传', async () => {
    const abortErr = new DOMException('The operation was aborted.', 'AbortError')
    let i = 0
    const bad = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i++ === 0) controller.enqueue(new TextEncoder().encode('event: token\ndata: {"content":"a"}\n\n'))
        else controller.error(abortErr)
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(bad, { status: 200 })))
    const err = await captureRejection(streamChat({ message: '你好' }, makeHandlers()))
    expect(err).toBe(abortErr)
  })

  it('2xx 但无正文:reject STREAM_INTERRUPTED(响应无正文)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 200 })))
    const err = await captureRejection(streamChat({ message: '你好' }, makeHandlers())) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe('STREAM_INTERRUPTED')
    expect(err.message).toBe('响应无正文')
  })

  it('token 载荷不合规时忽略(轻量守卫)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(streamOf(
      'event: start\ndata: {"message_id":"m1","conversation_id":"conv1"}\n\n',
      'event: token\ndata: {"content":123}\n\n',
      'event: token\ndata: "raw"\n\n',
      'event: token\ndata: {"content":"ok"}\n\n',
      'event: done\ndata: {"qa_record_id":1,"conversation_id":"conv1","message_id":"m1"}\n\n',
    ), { status: 200 })))
    const h = makeHandlers()
    await streamChat({ message: '你好' }, h)
    expect(h.onToken).toHaveBeenCalledTimes(1)
    expect(h.onToken).toHaveBeenCalledWith({ content: 'ok' })
  })
})
