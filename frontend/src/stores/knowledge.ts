import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as kbApi from '@/api/knowledge'
import type { KnowledgeBase } from '@/api/types'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const list = ref<KnowledgeBase[]>([])
  const loading = ref(false)

  const enabledList = computed(() => list.value.filter((k) => k.is_enabled))

  async function load() {
    loading.value = true
    try {
      const paged = await kbApi.listKnowledgeBases()
      list.value = paged.items
    } finally {
      loading.value = false
    }
  }

  return { list, loading, enabledList, load }
})
