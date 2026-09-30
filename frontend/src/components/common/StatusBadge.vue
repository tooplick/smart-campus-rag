<script setup lang="ts">
import { computed } from 'vue'
import type { DocStatus } from '@/api/types'

const props = defineProps<{ status: DocStatus | string }>()

const map: Record<string, { label: string; cls: string }> = {
  pending: { label: '待处理', cls: 'bg-muted text-muted-foreground' },
  processing: { label: '处理中', cls: 'bg-blue-100 text-blue-700' },
  completed: { label: '已完成', cls: 'bg-emerald-100 text-emerald-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
}
const info = computed(() => map[props.status] ?? { label: props.status, cls: 'bg-muted text-muted-foreground' })
</script>

<template>
  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs" :class="info.cls">{{ info.label }}</span>
</template>
