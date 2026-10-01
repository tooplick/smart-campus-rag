<script setup lang="ts">
// 统一分页:共 N 条区间 + 页码 + 上/下一页;页码先经 v-model:page 写回父级,
// 再发 change 事件让父级刷新——两阶段分开,保证 load() 读到的一定是新页码
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { Button } from '@/components/ui/button'

const props = defineProps<{ total: number; pageSize: number }>()
const page = defineModel<number>('page', { required: true })
const emit = defineEmits<{ change: [page: number] }>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const range = computed(() => {
  if (props.total === 0) return '共 0 条'
  const from = (page.value - 1) * props.pageSize + 1
  const to = Math.min(page.value * props.pageSize, props.total)
  return from === to ? `第 ${from} 条 / 共 ${props.total} 条` : `第 ${from}-${to} 条 / 共 ${props.total} 条`
})

function go(p: number) {
  const next = Math.min(Math.max(1, p), pageCount.value)
  if (next === page.value) return
  page.value = next
  emit('change', next)
}
</script>

<template>
  <div v-if="total > 0" class="flex items-center justify-between text-sm text-muted-foreground">
    <span>{{ range }}</span>
    <div class="flex items-center gap-2">
      <span>第 {{ page }}/{{ pageCount }} 页</span>
      <Button variant="outline" size="sm" :disabled="page <= 1" @click="go(page - 1)">
        <ChevronLeft class="h-4 w-4" /> 上一页
      </Button>
      <Button variant="outline" size="sm" :disabled="page >= pageCount" @click="go(page + 1)">
        下一页 <ChevronRight class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>
