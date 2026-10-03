<script setup lang="ts">
// 知识库管理:列表(分页) + 新建/编辑/启停/删除 + 查看关联文档
// 状态覆盖:加载骨架 → 错误态(可重试) → 空态;删除确认与启停均有防重复提交
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { AlertCircle, Plus, Pencil, Trash2, FileText, Database } from '@lucide/vue'
import * as kbApi from '@/api/knowledge'
import type { KnowledgeBase } from '@/api/types'
import { errorMessage } from '@/utils/request'
import { formatTime } from '@/utils/format'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import KbFormDialog from '@/components/knowledge/KbFormDialog.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TableSkeleton from '@/components/common/TableSkeleton.vue'
import Pagination from '@/components/common/Pagination.vue'

const router = useRouter()
const items = ref<KnowledgeBase[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)
// 骨架仅在首屏显示,动作后的重载保持表格稳定(防整表闪烁)
const hasLoaded = ref(false)
const showSkeleton = computed(() => loading.value && !hasLoaded.value && !failed.value)

const dialogOpen = ref(false)
const editing = ref<KnowledgeBase | null>(null)
const deleteTarget = ref<KnowledgeBase | null>(null)
const confirmOpen = ref(false)
const deleting = ref(false)
const togglingId = ref<number | null>(null)

/** 加载当前页知识库列表 */
async function load() {
  loading.value = true
  failed.value = false
  try {
    const paged = await kbApi.listKnowledgeBases(page.value, pageSize)
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

/** 打开新建对话框 */
function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

/** 打开编辑对话框 */
function openEdit(row: KnowledgeBase) {
  editing.value = row
  dialogOpen.value = true
}

/** 新建或更新知识库后刷新列表 */
async function onSave(body: { name: string; description?: string; icon?: string }) {
  try {
    if (editing.value) await kbApi.updateKnowledgeBase(editing.value.id, body)
    else await kbApi.createKnowledgeBase(body)
    toast.success('保存成功')
    await load()
  } catch (e) {
    toast.error(errorMessage(e))
  }
}

/** 切换知识库启用状态(请求期间禁用该行开关防重复) */
async function onToggleEnabled(row: KnowledgeBase, v: boolean) {
  if (togglingId.value !== null) return
  togglingId.value = row.id
  try {
    await kbApi.updateKnowledgeBase(row.id, { is_enabled: v })
    row.is_enabled = v
    toast.success(v ? '已启用' : '已禁用')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    togglingId.value = null
  }
}

/** 弹出删除确认 */
function askDelete(row: KnowledgeBase) {
  deleteTarget.value = row
  confirmOpen.value = true
}

/** 确认删除知识库(deleting 防止确认按钮连点) */
async function onConfirmDelete() {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  try {
    await kbApi.deleteKnowledgeBase(deleteTarget.value.id)
    toast.success('已删除')
    await load()
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    deleting.value = false
  }
}

/** 跳转到该知识库的文档列表 */
function gotoDocuments(row: KnowledgeBase) {
  router.push({ path: '/Documents', query: { kb: row.id } })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">知识库管理</h1>
      <Button @click="openCreate">
        <Plus class="mr-1 h-4 w-4" /> 新建知识库
      </Button>
    </div>

    <TableSkeleton v-if="showSkeleton" :rows="5" :cols="7" />

    <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="知识库加载失败">
      <template #action>
        <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
      </template>
    </EmptyState>

    <Table v-else-if="items.length">
      <TableHeader>
        <TableRow>
          <TableHead>名称</TableHead>
          <TableHead>描述</TableHead>
          <TableHead>文档数</TableHead>
          <TableHead>Chunk 数</TableHead>
          <TableHead>启用</TableHead>
          <TableHead>更新时间</TableHead>
          <TableHead class="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="row in items" :key="row.id">
          <TableCell class="font-medium">{{ row.name }}</TableCell>
          <!-- 描述列:超宽截断,悬浮 title 显示全文 -->
          <TableCell class="max-w-56 truncate text-muted-foreground" :title="row.description ?? ''">
            {{ row.description || '—' }}
          </TableCell>
          <TableCell>{{ row.document_count }}</TableCell>
          <TableCell>{{ row.chunk_count }}</TableCell>
          <TableCell>
            <Switch :model-value="row.is_enabled" :disabled="togglingId === row.id"
              @update:model-value="(v) => onToggleEnabled(row, Boolean(v))" />
          </TableCell>
          <TableCell>{{ formatTime(row.updated_at) }}</TableCell>
          <TableCell class="text-right">
            <div class="flex justify-end gap-1">
              <Button variant="ghost" size="icon" title="查看文档" @click="gotoDocuments(row)">
                <FileText class="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" title="编辑" @click="openEdit(row)">
                <Pencil class="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" title="删除" @click="askDelete(row)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
    <EmptyState v-else :icon="Database" title="暂无知识库" description="点击右上角创建第一个知识库" />

    <Pagination v-model:page="page" :total="total" :page-size="pageSize" @change="load" />

    <KbFormDialog v-model:open="dialogOpen" :editing="editing" @save="onSave" />
    <ConfirmDialog v-model:open="confirmOpen" title="删除知识库"
      :description="`确认删除「${deleteTarget?.name}」?其下所有文档与向量将一并删除,不可恢复。`" @confirm="onConfirmDelete" />
  </div>
</template>
