import { ApiError, normalizeError } from './request'
import { getClientId } from './auth'

export interface SseEvent<T = unknown> {
  event: string
  data: T
}

/** 聊天引用来源载荷(与后端 sources 事件一致) */
export interface ChatSource {
  chunk_id: string
  document_id: number
  filename: string
  page_number: number | null
  section_title: string | null
  content: string
  similarity_score: number
  source_order: number
}

/** start 事件载荷 */
export type ChatStartPayload = { message_id: string; conversation_id: string }
/** token 事件载荷 */
export type ChatTokenPayload = { content: string }
/** sources 事件载荷 */
export type ChatSourcesPayload = { sources: ChatSource[] }
/** done 事件载荷 */
export type ChatDonePayload = { qa_record_id: number; conversation_id: string; message_id: string }
/** error 事件线上传输载荷(仅用于构造 ApiError) */
export type ChatErrorPayload = { code: string; message: string }

/** 轻量载荷守卫:必须是非 null 对象 */
function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null
}

/** 增量 SSE 解析器:按空行切分事件块,支持跨 chunk 重组 */
export function createSseParser(onEvent: (e: SseEvent) => void) {
  let buffer = ''
  function parseBlock(block: string) {
    let event = 'message'
    const dataLines: string[] = []
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (dataLines.length === 0) return
    let data: unknown = dataLines.join('\n')
    try { data = JSON.parse(data as string) } catch { /* 非 JSON 原样传出 */ }
    onEvent({ event, data })
  }
  return {
    feed(chunk: string) {
      buffer = (buffer + chunk).replace(/\r\n/g, '\n')
      let sep: number
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)
        if (block.trim()) parseBlock(block)
      }
    },
    flush() {
      // SSE 规范:流末尾未以空行终结的块不完整,不派发,直接丢弃
      buffer = ''
    },
  }
}

export interface ChatStreamHandlers {
  onStart: (d: ChatStartPayload) => void
  onToken: (d: ChatTokenPayload) => void
  onSources: (d: ChatSourcesPayload) => void
  onDone: (d: ChatDonePayload) => void
  onError: (err: ApiError) => void
}

/**
 * POST /api/chat 流式请求,按事件分发回调。
 * 终态契约:成功仅 resolve 一次(收到 done);一切失败均 reject(ApiError 或 AbortError)。
 */
export async function streamChat(
  body: { conversation_id?: string | null; knowledge_base_id?: number | null; message: string },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const clientId = getClientId()
  let res: Response
  try {
    res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(clientId ? { 'X-Client-ID': clientId } : {}) },
      body: JSON.stringify({ ...body, stream: true }),
      signal,
    })
  } catch (e) {
    // 用户主动中止保持原样,其余统一为网络错误(避免裸 TypeError 泄漏)
    if ((e as Error).name === 'AbortError') throw e
    throw new ApiError('网络错误,请检查连接后重试', 'NETWORK_ERROR', 0)
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw normalizeError(res.status, data)
  }
  if (!res.body) {
    // 2xx 但无正文:不走 normalizeError(200),避免误导文案
    throw new ApiError('响应无正文', 'STREAM_INTERRUPTED', 0)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let doneReceived = false
  const parser = createSseParser(({ event, data }) => {
    if (event === 'start') {
      if (isRecord(data)) handlers.onStart(data as ChatStartPayload)
    } else if (event === 'token') {
      // 轻量守卫:对象且含 content 字符串才派发,防御非规范上游
      if (isRecord(data) && typeof data.content === 'string') {
        handlers.onToken({ content: data.content })
      }
    } else if (event === 'sources') {
      if (isRecord(data)) handlers.onSources(data as ChatSourcesPayload)
    } else if (event === 'done') {
      doneReceived = true
      if (isRecord(data)) handlers.onDone(data as ChatDonePayload)
    } else if (event === 'error') {
      // 失败唯一通道:先回调 onError 供 UI 展示,再抛出同一 ApiError
      const d = isRecord(data) ? data : {}
      const err = new ApiError(
        typeof d.message === 'string' ? d.message : '请求失败',
        typeof d.code === 'string' ? d.code : 'STREAM_ERROR',
        200,
      )
      handlers.onError(err)
      throw err
    }
  })
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      parser.feed(decoder.decode(value, { stream: true }))
    }
  } catch (e) {
    // error 事件抛出的 ApiError 原样透传;AbortError 原样 rethrow;其余包成网络错误
    if (e instanceof ApiError) throw e
    if ((e as Error).name === 'AbortError') throw e
    throw new ApiError('网络错误,请检查连接后重试', 'NETWORK_ERROR', 0)
  }
  // 冲出被切断多字节序列的残余,再按规范丢弃不完整末尾块
  parser.feed(decoder.decode())
  parser.flush()
  if (!doneReceived) {
    throw new ApiError('回答流意外中断,请重试', 'STREAM_INTERRUPTED', 0)
  }
}
