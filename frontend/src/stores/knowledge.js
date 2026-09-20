import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as kbApi from '@/api/knowledgeBases.js'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const knowledgeBases = ref([])
  const activeKnowledgeBase = ref(null)
  const loading = ref(false)

  async function loadKnowledgeBases(page = 1, pageSize = 20) {
    loading.value = true
    try {
      const res = await kbApi.listKnowledgeBases(page, pageSize)
      if (res.success) {
        knowledgeBases.value = res.data.items || []
      }
      return res
    } finally {
      loading.value = false
    }
  }

  async function createKnowledgeBase(data) {
    const res = await kbApi.createKnowledgeBase(data)
    if (res.success) knowledgeBases.value.unshift(res.data)
    return res
  }

  async function updateKnowledgeBase(id, data) {
    const res = await kbApi.updateKnowledgeBase(id, data)
    if (res.success) {
      const idx = knowledgeBases.value.findIndex((kb) => kb.id === id)
      if (idx >= 0) knowledgeBases.value[idx] = res.data
    }
    return res
  }

  async function removeKnowledgeBase(id) {
    const res = await kbApi.deleteKnowledgeBase(id)
    if (res.success) {
      knowledgeBases.value = knowledgeBases.value.filter((kb) => kb.id !== id)
    }
    return res
  }

  return { knowledgeBases, activeKnowledgeBase, loading, loadKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, removeKnowledgeBase }
})
