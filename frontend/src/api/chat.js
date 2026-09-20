/**
 * Chat API - 独立于 Admin JWT，使用 X-Client-ID
 * SSE 使用 fetch + ReadableStream，不依赖 Axios interceptor
 */

function getClientId() {
  return localStorage.getItem('client_id') || ''
}

export async function getSession() {
  const resp = await fetch('/api/chat/session')
  const data = await resp.json()
  if (data.success && data.data?.client_id) {
    localStorage.setItem('client_id', data.data.client_id)
  }
  return data
}

/**
 * 流式聊天 - 使用 fetch + ReadableStream 解析 SSE
 */
export async function streamChat(params, callbacks = {}) {
  const { onStart, onToken, onSources, onDone, onError, onHttpError } = callbacks
  const controller = new AbortController()

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-ID': getClientId(),
      },
      body: JSON.stringify({
        conversation_id: params.conversation_id || null,
        knowledge_base_id: params.knowledge_base_id,
        message: params.message,
        stream: true,
      }),
      signal: controller.signal,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      if (onHttpError) onHttpError(response.status, errorData)
      return controller
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      let currentEvent = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            switch (currentEvent) {
              case 'start': onStart?.(data); break
              case 'token': onToken?.(data); break
              case 'sources': onSources?.(data); break
              case 'done': onDone?.(data); break
              case 'error': onError?.(data); break
            }
          } catch (e) { /* skip */ }
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      onHttpError?.(0, { message: err.message })
    }
  }

  return controller
}

/**
 * 非流式聊天
 */
export async function chat(params) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Client-ID': getClientId(),
    },
    body: JSON.stringify({
      conversation_id: params.conversation_id || null,
      knowledge_base_id: params.knowledge_base_id,
      message: params.message,
      stream: false,
    }),
  })
  return response.json()
}
