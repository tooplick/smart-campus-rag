<script setup lang="ts">
// 问答日志:分页列表 + 点击行打开详情抽屉
// 详情含:问题/Markdown 回答/检索来源卡片/按「基本 · RAG · 耗时 · Token」分组的明细
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { AlertCircle, FileText, ScrollText } from '@lucide/vue'
import type { QaLog, QaLogDetail } from '@/api/types'
import { errorMessage } from '@/utils/request'
import { formatTime, formatDuration } from '@/utils/format'
import { useAdminStore } from '@/stores/admin'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle,
} from '@/components/ui/drawer'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TableSkeleton from '@/components/common/TableSkeleton.vue'
import Pagination from '@/components/common/Pagination.vue'
import MarkdownRenderer from '@/components/chat/MarkdownRenderer.vue'

const admin = useAdminStore()
const items = ref<QaLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)
// 骨架仅在首屏显示,动作后的重载保持表格稳定(防整表闪烁)
const hasLoaded = ref(false)
const showSkeleton = computed(() => loading.value && !hasLoaded.value && !failed.value)

const drawerOpen = ref(false)
const detail = ref<QaLogDetail | null>(null)

async function load() {
  loading.value = true
  failed.value = false
  try {
    const paged = await admin.loadQaLogs({
      page: page.value, page_size: pageSize, sort_by: 'created_at', sort_order: 'desc',
    })
    items.value = paged.items
    total.value = paged.total
  } catch (e) {
    failed.value = true
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
    hasLoaded.value = true
  }
}

onMounted(load)

/** 点击行加载详情后打开抽屉 */
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

/** 相似度百分比文案 */
function scoreText(score: number) {
  return (score * 100).toFixed(1) + '%'
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold">问答日志</h1>

    <TableSkeleton v-if="showSkeleton" :rows="6" :cols="6" />

    <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="问答日志加载失败">
      <template #action>
        <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
      </template>
    </EmptyState>

    <Table v-else-if="items.length">
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
          <TableCell>
            <StatusBadge :status="badgeStatus(row.status)" />
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
    <EmptyState v-else :icon="ScrollText" title="暂无问答记录" />

    <Pagination v-model:page="page" :total="total" :page-size="pageSize" @change="load" />

    <Drawer v-model:open="drawerOpen">
      <DrawerContent class="max-h-[85vh] overflow-y-auto">
        <DrawerHeader>
          <DrawerTitle>问答详情</DrawerTitle>
        </DrawerHeader>
        <div v-if="detail" class="space-y-5 px-4 pb-8">
          <div>
            <p class="mb-1 text-xs text-muted-foreground">问题</p>
            <p class="text-sm">{{ detail.question }}</p>
          </div>
          <div>
            <p class="mb-1 text-xs text-muted-foreground">回答</p>
            <!-- 回答按 Markdown 渲染(与聊天侧一致),引用角标同样高亮 -->
            <MarkdownRenderer v-if="detail.answer" :content="detail.answer" />
            <p v-else class="text-sm text-muted-foreground">—</p>
          </div>
          <div v-if="detail.sources.length">
            <p class="mb-1 text-xs text-muted-foreground">检索来源({{ detail.sources.length }})</p>
            <!-- 来源卡片:文件名/页码/相似度 与 正文分层,对齐聊天侧引用卡片的信息层级 -->
            <div class="space-y-2">
              <div v-for="s in detail.sources" :key="s.chunk_id" class="rounded-lg border p-3">
                <div class="flex items-start gap-2">
                  <FileText class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-xs font-medium">{{ s.source_order }}. {{ s.filename }}</p>
                    <p class="text-xs text-muted-foreground">
                      <span v-if="s.page_number !== null">第 {{ s.page_number }} 页 · </span>
                      <span v-if="s.section_title">{{ s.section_title }} · </span>
                      相似度 {{ scoreText(s.similarity_score) }}
                    </p>
                  </div>
                  <span class="shrink-0 rounded bg-accent px-1 text-xs text-accent-foreground">{{ s.source_order
                    }}</span>
                </div>
                <p class="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">{{ s.content }}</p>
              </div>
            </div>
          </div>
          <!-- 明细按「基本 · RAG · 耗时 · Token」分组 -->
          <div class="space-y-3 rounded-lg border p-3 text-xs">
            <div>
              <p class="mb-1 font-medium">基本信息</p>
              <div class="grid grid-cols-2 gap-1 text-muted-foreground">
                <p>模型:{{ detail.model_name ?? '—' }}</p>
                <p>状态:{{ detail.status }}</p>
                <p>时间:{{ formatTime(detail.created_at) }}</p>
                <p>轮次:第 {{ detail.turn_index }} 轮</p>
              </div>
            </div>
            <div class="border-t pt-2">
              <p class="mb-1 font-medium">RAG 参数</p>
              <p class="text-muted-foreground">top_k={{ detail.rag.candidate_top_k }}/{{ detail.rag.final_top_k }},阈值={{
                detail.rag.similarity_threshold }}</p>
            </div>
            <div class="border-t pt-2">
              <p class="mb-1 font-medium">耗时</p>
              <div class="grid grid-cols-2 gap-1 text-muted-foreground">
                <p>检索:{{ detail.retrieval.count }} 条 / {{ formatDuration(detail.retrieval.latency_ms) }}</p>
                <p>LLM:{{ formatDuration(detail.llm.latency_ms) }}</p>
                <p>总耗时:{{ formatDuration(detail.latency.total_ms) }}</p>
              </div>
            </div>
            <div class="border-t pt-2">
              <p class="mb-1 font-medium">Token</p>
              <p class="text-muted-foreground">输入 {{ detail.tokens.prompt ?? 0 }} + 输出 {{ detail.tokens.completion ?? 0
                }} =
                共 {{ detail.tokens.total ?? 0 }}</p>
            </div>
            <p v-if="detail.error_message" class="border-t pt-2 text-destructive">错误:{{ detail.error_message }}</p>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  </div>
</template>
