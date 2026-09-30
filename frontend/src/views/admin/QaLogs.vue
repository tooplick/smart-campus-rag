<script setup lang="ts">
// 问答日志:分页列表 + 点击行打开详情抽屉(问题/回答/检索来源/耗时与 Token 明细)
import { onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { ScrollText } from '@lucide/vue'
import type { QaLog, QaLogDetail } from '@/api/types'
import { errorMessage } from '@/utils/request'
import { formatTime, formatDuration } from '@/utils/format'
import { useAdminStore } from '@/stores/admin'
import { Button } from '@/components/ui/button'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle,
} from '@/components/ui/drawer'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const admin = useAdminStore()
const items = ref<QaLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

const drawerOpen = ref(false)
const detail = ref<QaLogDetail | null>(null)

async function load() {
  loading.value = true
  try {
    const paged = await admin.loadQaLogs({
      page: page.value, page_size: pageSize, sort_by: 'created_at', sort_order: 'desc',
    })
    items.value = paged.items
    total.value = paged.total
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function openDetail(row: QaLog) {
  try {
    await admin.loadQaLogDetail(row.id)
    detail.value = admin.qaLogDetail
    drawerOpen.value = true
  } catch (e) {
    toast.error(errorMessage(e))
  }
}

/** qa_records.status 映射到 StatusBadge 四态 */
function badgeStatus(s: string) {
  if (s === 'success') return 'completed'
  if (s === 'failed') return 'failed'
  return 'processing'
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold">问答日志</h1>

    <Table v-if="items.length">
      <TableHeader>
        <TableRow>
          <TableHead>时间</TableHead>
          <TableHead>问题</TableHead>
          <TableHead>模型</TableHead>
          <TableHead>耗时</TableHead>
          <TableHead>Token</TableHead>
          <TableHead>状态</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="row in items" :key="row.id" class="cursor-pointer" @click="openDetail(row)">
          <TableCell>{{ formatTime(row.created_at) }}</TableCell>
          <TableCell class="max-w-80 truncate">{{ row.question }}</TableCell>
          <TableCell>{{ row.model_name ?? '—' }}</TableCell>
          <TableCell>{{ formatDuration(row.latency_ms) }}</TableCell>
          <TableCell>{{ row.total_tokens ?? '—' }}</TableCell>
          <TableCell><StatusBadge :status="badgeStatus(row.status)" /></TableCell>
        </TableRow>
      </TableBody>
    </Table>
    <EmptyState v-else-if="!loading" :icon="ScrollText" title="暂无问答记录" />

    <div v-if="total > pageSize" class="flex items-center justify-between text-sm text-muted-foreground">
      <span>共 {{ total }} 条</span>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" :disabled="page <= 1" @click="page--; load()">上一页</Button>
        <Button variant="outline" size="sm" :disabled="page * pageSize >= total" @click="page++; load()">下一页</Button>
      </div>
    </div>

    <Drawer v-model:open="drawerOpen">
      <DrawerContent class="max-h-[85vh] overflow-y-auto">
        <DrawerHeader>
          <DrawerTitle>问答详情</DrawerTitle>
        </DrawerHeader>
        <div v-if="detail" class="space-y-4 px-4 pb-8">
          <div>
            <p class="mb-1 text-xs text-muted-foreground">问题</p>
            <p class="text-sm">{{ detail.question }}</p>
          </div>
          <div>
            <p class="mb-1 text-xs text-muted-foreground">回答</p>
            <p class="whitespace-pre-wrap text-sm">{{ detail.answer }}</p>
          </div>
          <div v-if="detail.sources.length">
            <p class="mb-1 text-xs text-muted-foreground">检索来源({{ detail.sources.length }})</p>
            <div class="space-y-1">
              <div v-for="s in detail.sources" :key="s.chunk_id" class="rounded-md border p-2 text-xs">
                <p class="font-medium">{{ s.source_order }}. {{ s.filename }}
                  <span v-if="s.page_number !== null" class="text-muted-foreground">(第 {{ s.page_number }} 页)</span>
                </p>
                <p class="text-muted-foreground">相似度 {{ (s.similarity_score * 100).toFixed(1) }}% · {{ s.content }}</p>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2 rounded-md border p-3 text-xs">
            <p>模型:{{ detail.model_name ?? '—' }}</p>
            <p>状态:{{ detail.status }}</p>
            <p>RAG 参数:top_k={{ detail.rag.candidate_top_k }}/{{ detail.rag.final_top_k }},阈值={{ detail.rag.similarity_threshold }}</p>
            <p>检索:{{ detail.retrieval.count }} 条 / {{ formatDuration(detail.retrieval.latency_ms) }}</p>
            <p>LLM:{{ formatDuration(detail.llm.latency_ms) }}</p>
            <p>总耗时:{{ formatDuration(detail.latency.total_ms) }}</p>
            <p>Token:{{ detail.tokens.prompt ?? 0 }} + {{ detail.tokens.completion ?? 0 }} = {{ detail.tokens.total ?? 0 }}</p>
            <p v-if="detail.error_message" class="text-destructive">错误:{{ detail.error_message }}</p>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  </div>
</template>
