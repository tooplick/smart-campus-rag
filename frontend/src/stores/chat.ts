import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { toast } from 'vue-sonner'
import * as chatApi from '@/api/chat'
import { streamChat } from '@/utils/sse'
import { errorMessage } from '@/utils/request'
import { getClientId, setClientId } from '@/utils/auth'
import type { ConversationSummary, Source } from '@/api/types'

/** 前端消息模型:sources 仅当次 SSE 回答有,历史消息无 */
export interface UiMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  streaming?: boolean
  /** 回答生成失败:详细原因已 toast 弹出,气泡只留状态 + 重试入口 */
  failed?: boolean
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<ConversationSummary[]>([])
  const currentConversationId = ref<string | null>(null)
  const messages = ref<UiMessage[]>([])
  const sending = ref(false)
  const loadingHistory = ref(false)

  /** 确保 client_id 存在(匿名会话标识) */
  async function ensureSession() {
    if (getClientId()) return
    const { client_id } = await chatApi.fetchSession()
    setClientId(client_id)
  }

  async function loadConversations() {
    await ensureSession()
    const paged = await chatApi.listConversations()
    conversations.value = paged.items
  }

  function newConversation() {
    currentConversationId.value = null
    messages.value = []
  }

  async function openConversation(id: string) {
    loadingHistory.value = true
    try {
      const detail = await chatApi.getConversation(id)
      currentConversationId.value = detail.id
      // 历史消息接口不返回 sources,仅还原问答文本
      messages.value = detail.messages.map((m) => ({ role: m.role, content: m.content }))
    } finally {
      loadingHistory.value = false
    }
  }

  async function renameConversation(id: string, title: string) {
    await chatApi.renameConversation(id, title)
    const item = conversations.value.find((c) => c.id === id)
    if (item) item.title = title
  }

  async function removeConversation(id: string) {
    await chatApi.deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConversationId.value === id) newConversation()
  }

  /** 流式失败:详细报错(细化到模型配置)顶部居中 toast 弹出;气泡标记 failed 供重试入口 */
  function failAssistant(assistant: UiMessage, e: unknown) {
    assistant.streaming = false
    assistant.failed = true
    toast.error(errorMessage(e))
  }

  /** 发送问题,SSE 流式累积回答 */
  async function send(content: string) {
    if (sending.value) return
    sending.value = true
    messages.value.push({ role: 'user', content })
    // 用 reactive 包装:token 增量写入必须经代理才能触发视图更新
    const assistant = reactive<UiMessage>({ role: 'assistant', content: '', streaming: true })
    messages.value.push(assistant)
    try {
      await streamChat(
        {
          conversation_id: currentConversationId.value,
          // 不做前端知识库选择,自动检索全部知识库
          knowledge_base_id: null,
          message: content,
        },
        {
          onStart: (d) => {
            const isNew = !currentConversationId.value
            currentConversationId.value = d.conversation_id
            if (isNew) loadConversations().catch((e) => toast.error(errorMessage(e)))
          },
          onToken: (d) => { assistant.content += d.content },
          onSources: (d) => { assistant.sources = d.sources },
          onDone: () => {
            assistant.streaming = false
            loadConversations().catch((e) => toast.error(errorMessage(e)))
          },
          onError: (e) => {
            failAssistant(assistant, e)
          },
        },
      )
    } catch (e) {
      failAssistant(assistant, e)
    } finally {
      sending.value = false
    }
  }

  /** 重试最近一次失败的回答:移除该失败问答对后按原问题重发 */
  async function retryLast() {
    if (sending.value) return
    const msgs = messages.value
    const last = msgs[msgs.length - 1]
    if (!last || last.role !== 'assistant' || !last.failed) return
    const userMsg = msgs[msgs.length - 2]
    if (!userMsg || userMsg.role !== 'user') return
    const question = userMsg.content
    msgs.splice(msgs.length - 2, 2)
    await send(question)
  }

  return {
    conversations, currentConversationId, messages,
    sending, loadingHistory,
    ensureSession, loadConversations, newConversation, openConversation,
    renameConversation, removeConversation, send, retryLast,
  }
})
