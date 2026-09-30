import { describe, it, expect } from 'vitest'
import { createSseParser, type SseEvent } from './sse'

function collect() {
  const events: SseEvent[] = []
  const parser = createSseParser((e) => events.push(e))
  return { events, parser }
}

describe('createSseParser', () => {
  it('解析完整事件块', () => {
    const { events, parser } = collect()
    parser.feed('event: token\ndata: {"content":"你"}\n\n')
    expect(events).toEqual([{ event: 'token', data: { content: '你' } }])
  })

  it('跨 chunk 切断的事件能正确重组', () => {
    const { events, parser } = collect()
    parser.feed('event: tok')
    parser.feed('en\ndata: {"content":"好"}\n')
    parser.feed('\n')
    expect(events).toHaveLength(1)
    expect(events[0].event).toBe('token')
  })

  it('一次 feed 多个事件', () => {
    const { events, parser } = collect()
    parser.feed('event: start\ndata: {"message_id":"m1"}\n\nevent: done\ndata: {"qa_record_id":1}\n\n')
    expect(events.map((e) => e.event)).toEqual(['start', 'done'])
  })

  it('兼容 CRLF 换行', () => {
    const { events, parser } = collect()
    parser.feed('event: error\r\ndata: {"code":"LLM_ERROR"}\r\n\r\n')
    expect(events[0].event).toBe('error')
    expect(events[0].data).toEqual({ code: 'LLM_ERROR' })
  })

  it('flush 丢弃不完整末尾块', () => {
    const { events, parser } = collect()
    parser.feed('event: token\ndata: {"content":"x"}\n\nevent: token\ndata: {"content":"y"}')
    parser.flush()
    expect(events).toHaveLength(1)
    expect(events[0].data).toEqual({ content: 'x' })
  })
})
