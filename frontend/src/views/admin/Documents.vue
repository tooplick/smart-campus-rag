<script setup lang="ts">
// 文档管理:按知识库筛选 + 上传 + 状态/进度 + 2 秒轮询 + 重试/取消/删除
// 状态覆盖:加载骨架 → 错误态(可重试) → 空态;处理中不可删除(对齐后端 409)
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { AlertCircle, Upload, RotateCcw, X, Trash2, FileText, RefreshCw } from '@lucide/vue'
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
import TableSkeleton from '@/components/common/TableSkeleton.vue'
import Pagination from '@/components/common/Pagination.vue'
import UploadDialog from '@/components/document/UploadDialog.vue'

const route = useRoute()
const knowledge = useKnowledgeStore()

const kbId = ref<number | null>(route.query.kb ? Number(route.query.kb) : null)
const items = ref<DocFile[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)
// 首屏数据是否已到达:骨架仅在首屏显示,轮询刷新保持表格稳定
// (否则每 2 秒整表被骨架替换再换回,视觉上就是闪烁)
const hasLoaded = ref(false)
const showSkeleton = computed(() => loading.value && !hasLoaded.value && !failed.value)

const uploadOpen = ref(false)
const deleteTarget = ref<DocFile | null>(null)
const confirmOpen = ref(false)
const deleting = ref(false)

let timer: number | null = null
const polling = computed(() => timer !== null)

/** 加载当前页文档列表;silent 供轮询刷新:失败不弹提示、不切错误态,保留当前表格 */
async function load(opts?: { silent?: boolean }) {
  loading.value = true
  failed.value = false
  try {
    const paged = await listDocuments({
      knowledge_base_id: kbId.value ?? undefined,
      page: page.value, page_size: pageSize,
      sort_by: 'created_at', sort_order: 'desc',
    })
    items.value = paged.items
    total.value = paged.total
  } catch (e) {
    // 轮询失败静默:避免每 2 秒弹一次 toast
    if (opts?.silent) return
    failed.value = true
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
    hasLoaded.value = true
  }
}

/** 列表中还有处理中的文档时 2 秒轮询,否则停止 */
function schedulePoll() {
  if (timer) window.clearTimeout(timer)
  timer = null
  const hasActive = items.value.some((d) => d.status === 'pending' || d.status === 'processing')
  if (hasActive) timer = window.setTimeout(async () => { await load({ silent: true }); schedulePoll() }, 2000)
}

onMounted(async () => {
  await knowledge.load().catch(() => { })
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

/** 处理中(processing)文档禁止删除——对齐后端 409「处理中不可删,请先取消」 */
function cannotDelete(row: DocFile) {
  return row.status === 'processing'
}

/** 进度条宽度:待处理按 0% 展示,处理中取后端进度 */
function progressWidth(row: DocFile) {
  return (row.status === 'pending' ? 0 : row.progress) + '%'
}

/** 进度文字:处理中显示百分比 */
function progressText(row: DocFile) {
  return row.progress + '%'
}

/** 重新处理文档 */
async function onReprocess(row: DocFile) {
  try {
    await reprocessDocument(row.id)
    toast.success('已重新加入处理队列')
    await load(); schedulePoll()
  } catch (e) { toast.error(errorMessage(e)) }
}

/** 取消处理(后端仅允许 processing 状态取消) */
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

/** 确认删除文档(deleting 防止确认按钮连点) */
async function onConfirmDelete() {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  try {
    await deleteDocument(deleteTarget.value.id)
    toast.success('已删除')
    await load(); schedulePoll()
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    deleting.value = false
  }
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

    <div class="flex flex-wrap items-center gap-2">
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
      <!-- 轮询进行中的微标识:让用户知道列表在自动刷新 -->
      <span v-if="polling" class="flex items-center gap-1 text-xs text-muted-foreground">
        <RefreshCw class="h-3 w-3 animate-spin" /> 自动刷新中
      </span>
    </div>

    <TableSkeleton v-if="showSkeleton" :rows="5" :cols="7" />

    <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="文档列表加载失败">
      <template #action>
        <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="() => load()">重试</button>
      </template>
    </EmptyState>

    <Table v-else-if="items.length">
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
          <TableCell class="max-w-64 truncate font-medium" :title="row.filename">{{ row.filename }}</TableCell>
          <TableCell>{{ formatFileSize(row.file_size) }}</TableCell>
          <TableCell>{{ row.chunk_count }}</TableCell>
          <TableCell>
            <StatusBadge :status="row.status" />
            <!-- 错误信息超宽截断,悬浮 title 查看完整内容 -->
            <p v-if="row.error_message" class="mt-1 max-w-48 truncate text-xs text-destructive"
              :title="row.error_message">
              {{ row.error_message }}
            </p>
          </TableCell>
          <TableCell>
            <!-- 进度:处理中显示百分比;待处理显示排队中(0%);失败/完成给终值 -->
            <div v-if="row.status === 'processing' || row.status === 'pending'" class="flex items-center gap-2">
              <div class="h-2 w-20 overflow-hidden rounded bg-muted">
                <!-- 宽度平滑补间:轮询拿到新值后线性滑过去,而非跳变 -->
                <div class="h-2 rounded bg-primary transition-[width] duration-700 ease-out"
                  :style="{ width: progressWidth(row) }" />
              </div>
              <span class="text-xs text-muted-foreground">{{ row.status === 'pending' ? '排队中' : progressText(row)
              }}</span>
            </div>
            <span v-else class="text-xs text-muted-foreground">{{ row.status === 'completed' ? '100%' : '—' }}</span>
          </TableCell>
          <TableCell>{{ formatTime(row.created_at) }}</TableCell>
          <TableCell class="text-right">
            <div class="flex justify-end gap-1">
              <Button v-if="row.status === 'failed' || row.status === 'completed'" variant="ghost" size="icon"
                title="重新处理" @click="onReprocess(row)">
                <RotateCcw class="h-4 w-4" />
              </Button>
              <!-- 取消仅处理中可用(后端对非 processing 取消返回 409) -->
              <Button v-if="row.status === 'processing'" variant="ghost" size="icon" title="取消处理"
                @click="onCancel(row)">
                <X class="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" :disabled="cannotDelete(row)"
                :title="cannotDelete(row) ? '处理中不可删除,请先取消' : '删除'" @click="askDelete(row)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
    <EmptyState v-else :icon="FileText" title="暂无文档" description="选择知识库后上传文档(Office / 文本 / 网页 / 图片均可)" />

    <Pagination v-model:page="page" :total="total" :page-size="pageSize" @change="load().then(schedulePoll)" />

    <UploadDialog v-model:open="uploadOpen" :knowledge-base-id="kbId" @uploaded="load().then(schedulePoll)" />
    <ConfirmDialog v-model:open="confirmOpen" title="删除文档"
      :description="`确认删除「${deleteTarget?.filename}」?关联切片与向量将一并删除。`" @confirm="onConfirmDelete" />
  </div>
</template>
