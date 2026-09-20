import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSession } from '@/api/chat.js'
import { listKnowledgeBasesPublic } from '@/api/knowledgeBases.js'
import { listConversations, createConversation, getConversation, deleteConversation } from '@/api/conversations.js'

export const useChatStore = defineStore('chat', () => {
  const clientId = ref(localStorage.getItem('client_id') || '')
  const activeConversationId = ref(null)
  const conversations = ref([])
  const messages = ref([])
  const knowledgeBases = ref([])
  const selectedKnowledgeBase = ref(null)
  const streaming = ref(false)

  async function ensureClientId() {
    if (!clientId.value) {
      const res = await getSession()
      if (res.success) {
        clientId.value = res.data.client_id
      }
    }
    return clientId.value
  }

  async function loadKnowledgeBases() {
    const res = await listKnowledgeBasesPublic()
    if (res.success) {
      knowledgeBases.value = res.data.items || []
    }
  }

  async function loadConversations() {
    await ensureClientId()
    const res = await listConversations()
    if (res.success) {
      conversations.value = res.data.items || []
    }
  }

  async function newConversation(knowledgeBaseId, title = '新对话') {
    await ensureClientId()
    const res = await createConversation(knowledgeBaseId, title)
    if (res.success) {
      activeConversationId.value = res.data.id
      conversations.value.unshift(res.data)
      messages.value = []
      return res.data
    }
    return null
  }

  async function resumeConversation(id) {
    await ensureClientId()
    const res = await getConversation(id)
    if (res.success) {
      activeConversationId.value = id
      messages.value = res.data.messages || []
      return res.data
    }
    return null
  }

  async function removeConversation(id) {
    await ensureClientId()
    await deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (activeConversationId.value === id) {
      activeConversationId.value = null
      messages.value = []
    }
  }

  function addMessage(role, content) {
    messages.value.push({ role, content })
  }

  function appendToken(content) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += content
    } else {
      messages.value.push({ role: 'assistant', content })
    }
  }

  return {
    clientId, activeConversationId, conversations, messages,
    knowledgeBases, selectedKnowledgeBase, streaming,
    ensureClientId, loadKnowledgeBases, loadConversations,
    newConversation, resumeConversation, removeConversation,
    addMessage, appendToken,
  }
})
