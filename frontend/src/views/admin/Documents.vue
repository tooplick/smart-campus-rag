<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { Upload, RotateCcw, X, Trash2, FileText } from '@lucide/vue'
import {
  listDocuments, deleteDocument, reprocessDocument, cancelDocument,
} from '@/api/documents'
import type { DocFile } from '@/api/types'
import { errorMessage } from '@/utils/request'
import { formatTime, formatFileSize } from '@/utils/format'
import { useKnowledgeStore } from '@/stores/knowledge'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import UploadDialog from '@/components/document/UploadDialog.vue'

const route = useRoute()
const knowledge = useKnowledgeStore()

const kbId = ref<number | null>(route.query.kb ? Number(route.query.kb) : null)
const items = ref<DocFile[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

const uploadOpen = ref(false)
const deleteTarget = ref<DocFile | null>(null)
const confirmOpen = ref(false)

let timer: number | null = null

/** 加载当前页文档列表 */
async function load() {
  loading.value = true
  try {
    const paged = await listDocuments({
      knowledge_base_id: kbId.value ?? undefined,
      page: page.value, page_size: pageSize,
      sort_by: 'created_at', sort_order: 'desc',
    })
    items.value = paged.items
    total.value = paged.total
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}

/** 列表中还有处理中的文档时 2 秒轮询,否则停止 */
function schedulePoll() {
  if (timer) window.clearTimeout(timer)
  const hasActive = items.value.some((d) => d.status === 'pending' || d.status === 'processing')
  if (hasActive) timer = window.setTimeout(async () => { await load(); schedulePoll() }, 2000)
}

onMounted(async () => {
  await knowledge.load().catch(() => {})
  await load()
  schedulePoll()
})

onUnmounted(() => { if (timer) window.clearTimeout(timer) })

/** 切换知识库筛选后重新加载 */
function onKbChange(v: unknown) {
  const s = String(v ?? 'all')
  kbId.value = s === 'all' ? null : Number(s)
  page.value = 1
  load().then(schedulePoll)
}

/** 重新处理文档 */
async function onReprocess(row: DocFile) {
  try {
    await reprocessDocument(row.id)
    toast.success('已重新加入处理队列')
    await load(); schedulePoll()
  } catch (e) { toast.error(errorMessage(e)) }
}

/** 取消处理中的文档 */
async function onCancel(row: DocFile) {
  try {
    await cancelDocument(row.id)
    toast.success('已取消处理')
    await load(); schedulePoll()
  } catch (e) { toast.error(errorMessage(e)) }
}

/** 弹出删除确认 */
function askDelete(row: DocFile) {
  deleteTarget.value = row
  confirmOpen.value = true
}

/** 确认删除文档 */
async function onConfirmDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteDocument(deleteTarget.value.id)
    toast.success('已删除')
    await load(); schedulePoll()
  } catch (e) { toast.error(errorMessage(e)) }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">文档管理</h1>
      <Button :disabled="kbId === null" @click="uploadOpen = true">
        <Upload class="mr-1 h-4 w-4" /> 上传文档
      </Button>
    </div>

    <div class="flex items-center gap-2">
      <Select :model-value="kbId === null ? 'all' : String(kbId)" @update:model-value="onKbChange">
        <SelectTrigger class="w-56">
          <SelectValue placeholder="全部知识库" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部知识库</SelectItem>
          <SelectItem v-for="kb in knowledge.list" :key="kb.id" :value="String(kb.id)">{{ kb.name }}</SelectItem>
        </SelectContent>
      </Select>
      <p v-if="kbId === null" class="text-sm text-muted-foreground">上传前请先选择目标知识库</p>
    </div>

    <Table v-if="items.length">
      <TableHeader>
        <TableRow>
          <TableHead>文件名</TableHead>
          <TableHead>大小</TableHead>
          <TableHead>Chunk 数</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>进度</TableHead>
          <TableHead>创建时间</TableHead>
          <TableHead class="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="row in items" :key="row.id">
          <TableCell class="max-w-64 truncate font-medium">{{ row.filename }}</TableCell>
          <TableCell>{{ formatFileSize(row.file_size) }}</TableCell>
          <TableCell>{{ row.chunk_count }}</TableCell>
          <TableCell>
            <StatusBadge :status="row.status" />
            <p v-if="row.error_message" class="mt-1 max-w-48 truncate text-xs text-destructive">{{ row.error_message }}</p>
          </TableCell>
          <TableCell>
            <div v-if="row.status === 'processing'" class="h-2 w-24 overflow-hidden rounded bg-muted">
              <div class="h-2 rounded bg-primary transition-all" :style="{ width: row.progress + '%' }" />
            </div>
            <span v-else class="text-xs text-muted-foreground">{{ row.status === 'completed' ? '100%' : '—' }}</span>
          </TableCell>
          <TableCell>{{ formatTime(row.created_at) }}</TableCell>
          <TableCell class="text-right">
            <div class="flex justify-end gap-1">
              <Button v-if="row.status === 'failed' || row.status === 'completed'" variant="ghost" size="icon"
                title="重新处理" @click="onReprocess(row)"><RotateCcw class="h-4 w-4" /></Button>
              <Button v-if="row.status === 'processing' || row.status === 'pending'" variant="ghost" size="icon"
                title="取消处理" @click="onCancel(row)"><X class="h-4 w-4" /></Button>
              <Button variant="ghost" size="icon" title="删除" @click="askDelete(row)"><Trash2 class="h-4 w-4" /></Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
    <EmptyState v-else-if="!loading" :icon="FileText" title="暂无文档" description="选择知识库后上传 PDF / DOCX / TXT 文档" />

    <div v-if="total > pageSize" class="flex items-center justify-between text-sm text-muted-foreground">
      <span>共 {{ total }} 条</span>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" :disabled="page <= 1" @click="page--; load()">上一页</Button>
        <Button variant="outline" size="sm" :disabled="page * pageSize >= total" @click="page++; load()">下一页</Button>
      </div>
    </div>

    <UploadDialog v-model:open="uploadOpen" :knowledge-base-id="kbId" @uploaded="load().then(schedulePoll)" />
    <ConfirmDialog v-model:open="confirmOpen" title="删除文档"
      :description="`确认删除「${deleteTarget?.filename}」?关联切片与向量将一并删除。`"
      @confirm="onConfirmDelete" />
  </div>
</template>
