<script setup lang="ts">
import { computed } from 'vue'
import { Trash2, Pencil } from '@lucide/vue'

const props = defineProps<{
  conversation: { id: string; title: string; updated_at: string }
  active?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  rename: [conversation: { id: string; title: string }]
  delete: [id: string]
}>()

const timeLabel = computed(() => {
  const d = new Date(props.conversation.updated_at)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay} 天前`
  return d.toLocaleDateString('zh-CN')
})
</script>

<template>
  <div
    class="group flex items-center gap-2 rounded-lg px-3 py-2.5 cursor-pointer transition-colors"
    :class="active ? 'bg-primary/10' : 'hover:bg-muted'"
    @click="emit('select', conversation.id)"
  >
    <div class="flex-1 min-w-0">
      <div
        class="text-sm font-medium truncate"
        :class="active ? 'text-primary' : 'text-foreground'"
      >
        {{ conversation.title }}
      </div>
      <div class="text-xs text-muted-foreground mt-0.5">{{ timeLabel }}</div>
    </div>
    <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        @click.stop="emit('rename', conversation)"
        class="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
      >
        <Pencil class="h-3.5 w-3.5" />
      </button>
      <button
        @click.stop="emit('delete', conversation.id)"
        class="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
      >
        <Trash2 class="h-3.5 w-3.5" />
      </button>
    </div>
  </div>
</template>
