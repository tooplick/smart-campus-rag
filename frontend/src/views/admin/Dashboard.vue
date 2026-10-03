<script setup lang="ts">
// 管理端仪表盘:统计卡片 + 问答趋势 / 文档状态 / 知识库分布三张图表
// 状态覆盖:加载骨架 → 错误态(可重试) → 图表无数据显示占位而非空坐标轴
import { computed, onMounted, ref } from 'vue'
import { AlertCircle, Database, FileText, Layers, MessageSquare } from '@lucide/vue'
import type { EChartsOption } from 'echarts'
import { toast } from 'vue-sonner'
import { errorMessage } from '@/utils/request'
import { useAdminStore } from '@/stores/admin'
import Chart from '@/components/admin/Chart.vue'
import { Skeleton } from '@/components/ui/skeleton'
import EmptyState from '@/components/common/EmptyState.vue'

const admin = useAdminStore()
const loading = ref(true)
// 失败仅驱动「通用错误态 + 重试」,具体原因走顶部居中 toast
const failed = ref(false)

async function load() {
  loading.value = true
  failed.value = false
  try {
    await admin.loadDashboard()
  } catch (e) {
    failed.value = true
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}

onMounted(load)

/** 顶部统计卡片数据 */
const stats = computed(() => {
  const s = admin.dashboard?.statistics
  return [
    { label: '知识库数量', value: s?.knowledge_base_count ?? 0, icon: Database },
    { label: '文档数量', value: s?.document_count ?? 0, icon: FileText },
    { label: 'Chunk 数量', value: s?.chunk_count ?? 0, icon: Layers },
    { label: '问答次数', value: s?.qa_count ?? 0, icon: MessageSquare },
  ]
})

/** 各图表是否有数据(无数据时渲染占位,避免空坐标轴) */
const hasTrend = computed(() => (admin.dashboard?.qa_trend.length ?? 0) > 0)
const hasStatus = computed(() => {
  const d = admin.dashboard?.document_status
  return Boolean(d && (d.pending || d.processing || d.completed || d.failed))
})
const hasDist = computed(() => (admin.dashboard?.knowledge_base_distribution.length ?? 0) > 0)

/** 问答趋势(近 7 天)折线图 */
const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 24, bottom: 32 },
  xAxis: { type: 'category', data: admin.dashboard?.qa_trend.map((t) => t.date) ?? [] },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data: admin.dashboard?.qa_trend.map((t) => t.count) ?? [] }],
}))

/** 文档处理状态环形图 */
const statusOption = computed<EChartsOption>(() => {
  const d = admin.dashboard?.document_status
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { name: '待处理', value: d?.pending ?? 0 },
        { name: '处理中', value: d?.processing ?? 0 },
        { name: '已完成', value: d?.completed ?? 0 },
        { name: '失败', value: d?.failed ?? 0 },
      ],
    }],
  }
})

/** 知识库文档分布横向柱状图 */
const distOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 100, right: 16, top: 16, bottom: 32 },
  xAxis: { type: 'value', minInterval: 1 },
  yAxis: {
    type: 'category',
    data: admin.dashboard?.knowledge_base_distribution.map((k) => k.name) ?? [],
  },
  series: [{
    type: 'bar',
    data: admin.dashboard?.knowledge_base_distribution.map((k) => k.document_count) ?? [],
  }],
}))
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold">仪表盘</h1>

    <!-- 加载:统计卡与图表骨架 -->
    <template v-if="loading">
      <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div v-for="i in 4" :key="i" class="space-y-3 rounded-lg border bg-background p-4">
          <Skeleton class="h-4 w-20" />
          <Skeleton class="h-8 w-16" />
        </div>
      </div>
      <div class="grid gap-4 lg:grid-cols-2">
        <Skeleton v-for="i in 3" :key="i" class="h-72 rounded-lg" :class="i === 3 ? 'lg:col-span-2' : ''" />
      </div>
    </template>

    <!-- 失败:toast 弹具体原因,页面留通用错误态 + 重试 -->
    <EmptyState v-else-if="failed" :icon="AlertCircle" variant="error" title="仪表盘加载失败">
      <template #action>
        <button class="rounded-md border px-4 py-2 text-sm hover:bg-accent" @click="load">重试</button>
      </template>
    </EmptyState>

    <template v-else>
      <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div v-for="s in stats" :key="s.label"
          class="rounded-lg border bg-background p-4 transition-shadow hover:shadow-md">
          <div class="flex items-center justify-between">
            <p class="text-sm text-muted-foreground">{{ s.label }}</p>
            <component :is="s.icon" class="h-4 w-4 text-muted-foreground" />
          </div>
          <p class="mt-2 text-2xl font-semibold">{{ s.value }}</p>
        </div>
      </div>
      <div class="grid gap-4 lg:grid-cols-2">
        <div class="rounded-lg border bg-background p-4">
          <p class="mb-2 text-sm font-medium">问答趋势(近 7 天)</p>
          <Chart v-if="hasTrend" :option="trendOption" />
          <p v-else class="flex h-64 items-center justify-center text-sm text-muted-foreground">近 7 天暂无问答</p>
        </div>
        <div class="rounded-lg border bg-background p-4">
          <p class="mb-2 text-sm font-medium">文档处理状态</p>
          <Chart v-if="hasStatus" :option="statusOption" />
          <p v-else class="flex h-64 items-center justify-center text-sm text-muted-foreground">暂无文档</p>
        </div>
        <div class="rounded-lg border bg-background p-4 lg:col-span-2">
          <p class="mb-2 text-sm font-medium">知识库文档分布</p>
          <Chart v-if="hasDist" :option="distOption" />
          <p v-else class="flex h-64 items-center justify-center text-sm text-muted-foreground">暂无知识库文档</p>
        </div>
      </div>
    </template>
  </div>
</template>
